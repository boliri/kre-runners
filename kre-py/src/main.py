import asyncio
import copy
import gc
import importlib.util
import inspect
import os
import sys
import traceback
from datetime import datetime

from google.protobuf.message import Message
from nats.errors import ConnectionClosedError, TimeoutError
from nats.js.api import ConsumerConfig, DeliverPolicy

from compression import compress_if_needed, is_compressed, uncompress
from config import Config
from context import HandlerContext
from handlers import HandlerManager
from kre_nats_msg_pb2 import ERROR, KreNatsMessage, MessageType
from kre_runner import Runner


class NodeRunner(Runner):
    def __init__(self):
        config: Config = Config()
        name = f"{config.krt_version}-{config.krt_node_name}"
        Runner.__init__(self, name, config)
        self.handler_ctx = None
        self.handler_init_fn = None
        self.handler_manager = None
        self.load_handler()

    def load_handler(self) -> None:
        self.logger.info(f"Loading handler script {self.config.handler_path}...")

        handler_full_path = os.path.join(self.config.base_path, self.config.handler_path)
        handler_dirname = os.path.dirname(handler_full_path)
        sys.path.append(handler_dirname)

        try:
            spec = importlib.util.spec_from_file_location("worker", handler_full_path)
            handler_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(handler_module)
        except Exception as err:
            tb = traceback.format_exc()
            self.logger.error(
                f"Error loading handler script {self.config.handler_path}: {err}\n\n{tb}"
            )
            sys.exit(1)

        default_handler = None
        if hasattr(handler_module, "default_handler"):
            default_handler = handler_module.default_handler

        custom_handlers = None
        if hasattr(handler_module, "custom_handlers"):
            custom_handlers = handler_module.custom_handlers

        if hasattr(handler_module, "init"):
            self.handler_init_fn = handler_module.init

        self.handler_manager = HandlerManager(default_handler, custom_handlers)
        self.logger.info(f"Handler script was loaded from '{handler_full_path}'")

    async def execute_handler_init(self) -> None:
        self.logger.info(f"Creating handler context...")
        self.handler_ctx = HandlerContext(
            self.config,
            self.nc,
            self.js,
            self.mongo_conn,
            self.logger,
            self.__publish_msg__,
            self.__publish_any__,
            self.configuration,
        )

        if not self.handler_init_fn:
            return

        self.logger.info(f"Executing handler init...")

        if inspect.iscoroutinefunction(self.handler_init_fn):
            await asyncio.create_task(self.handler_init_fn(self.handler_ctx))
        else:
            self.handler_init_fn(self.handler_ctx)

    async def process_messages(self) -> None:
        await self.execute_handler_init()

        for subject in self.config.nats_inputs:
            queue = f'{subject.replace(".", "-")}-{self.config.krt_node_name}'
            try:
                sub = await self.js.subscribe(
                    stream=self.config.nats_stream,
                    subject=subject,
                    queue=queue,
                    durable=queue,
                    cb=self.create_message_cb(),
                    config=ConsumerConfig(
                        deliver_policy=DeliverPolicy.NEW,
                        ack_wait=22 * 3600,  # 22 hours
                    ),
                    manual_ack=True,
                )
                self.subscription_sids.append(sub)
                self.logger.info(f"Listening to '{subject}' subject with queue group '{queue}'")

            except Exception as err:
                tb = traceback.format_exc()
                self.logger.error(f"Error subscribing to NATS subject {subject}: {err}\n\n{tb}")
                sys.exit(1)

    def create_message_cb(self) -> callable:
        async def message_cb(msg) -> None:
            """
            Callback for processing a message.

            :param msg: The message to process.
            """

            start = datetime.utcnow()

            request_msg = self.new_request_msg(msg.data)

            self.logger.info(
                f"Received a message from {msg.subject} with requestID {request_msg.request_id}"
            )

            try:
                # Make a shallow copy of the ctx object to set inside the request msg
                ctx = copy.copy(self.handler_ctx)
                ctx.set_request_msg(request_msg)

                handler = self.handler_manager.get_handler(request_msg.from_node)
                await handler(ctx, request_msg.payload)

                end = datetime.utcnow()
                self.save_elapsed_time(start, end, request_msg.from_node, True)

            except Exception as err:
                tb = traceback.format_exc()
                self.logger.error(f"Error executing handler: {err} \n\n{tb}")
                error_message = f"Error in node '{self.config.krt_node_name}' executing handler for node '{request_msg.from_node}': {str(err)}"
                await self.__publish_error__(request_msg.request_id, error_message)

                end = datetime.utcnow()
                self.save_elapsed_time(start, end, request_msg.from_node, False)

            # Tell NATS we don't need to receive the message anymore and we are done processing it
            await msg.ack()
            gc.collect()

        return message_cb

    @staticmethod
    def new_request_msg(data: bytes) -> KreNatsMessage:
        if is_compressed(data):
            data = uncompress(data)

        request_msg = KreNatsMessage()
        request_msg.ParseFromString(data)

        return request_msg

    async def __publish_msg__(
            self,
            response_payload: Message,
            request_msg: KreNatsMessage,
            msg_type: MessageType,
            channel: str,
    ):
        response_msg = self.new_response_msg(request_msg, msg_type)
        response_msg.payload.Pack(response_payload)
        await self.publish_response(response_msg, channel)

    async def __publish_any__(
            self, response_payload, request_msg: KreNatsMessage, msg_type: MessageType, channel: str
    ):
        response_msg = self.new_response_msg(request_msg, msg_type)
        response_msg.payload.CopyFrom(response_payload)
        await self.publish_response(response_msg, channel)

    async def __publish_error__(self, request_id: str, error_message: str, channel: str = ""):
        msg = KreNatsMessage()
        msg.request_id = request_id
        msg.error = error_message
        msg.from_node = self.config.krt_node_name
        msg.message_type = ERROR

        await self.publish_response(msg, channel)

    def new_response_msg(
            self, request_msg: KreNatsMessage, msg_type: MessageType
    ) -> KreNatsMessage:
        """
        Creates a KreNatsMessage that keeps previous request ID plus adding the payload we wish to send.

        :param  request_msg:  The KreNatsMessage request message from which this new msg will originate.
        :param msg_type:  The new KreNatsMessage MessageType.
        :return: KreNatsMessage.
        """

        res = KreNatsMessage()
        res.request_id = request_msg.request_id
        res.from_node = self.config.krt_node_name
        res.message_type = msg_type

        return res

    async def publish_response(self, response_msg: KreNatsMessage, channel: str) -> None:
        """
        Publish the response message to the output subject.

        :param  response_msg:  The response message to publish.
        :param channel:  The subject channel where the message will be published.
        :return: None.
        """

        stream_info = await self.js.stream_info(self.config.nats_stream)
        stream_max_size = stream_info.config.max_msg_size or -1
        server_max_size = self.nc.max_payload

        max_size = (
            min(stream_max_size, server_max_size) if stream_max_size != -1 else server_max_size
        )

        serialized_response_msg = compress_if_needed(
            response_msg.SerializeToString(), max_size=max_size, logger=self.logger
        )

        subject = self.__get_output_subject__(channel)

        try:
            await self.js.publish(
                stream=self.config.nats_stream, subject=subject, payload=serialized_response_msg
            )
            self.logger.info(f"Publishing response to {subject} subject")

        except ConnectionClosedError as err:
            self.logger.error(f"Connection closed when publishing response: {err}")
        except TimeoutError as err:
            self.logger.error(f"Timeout when publishing response: {err}")
        except Exception as err:
            self.logger.error(f"Error publishing response: {err}")

    def __get_output_subject__(self, channel: str = ""):
        output_subject = self.config.nats_output
        if channel == "":
            return output_subject
        return f"{output_subject}.{channel}"

    def save_elapsed_time(
            self, start: datetime, end: datetime, from_node: str, success: bool
    ) -> None:
        """
        Stores in InfluxDB how much time did it take the node to run the handler
        also saves if the request was succesfully processed.

        :param start: when this node started.
        :param end: when this node ended.
        :param success: was the request processed succesfully.
        :return: None.
        """

        elapsed = end - start
        tags = {
            "from_node": from_node,
        }

        fields = {
            "elapsed_ms": elapsed.total_seconds() * 1000,
            "success": success,
        }

        self.handler_ctx.measurement.save("node_elapsed_time", fields, tags)


if __name__ == "__main__":
    runner = NodeRunner()
    runner.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(runner.loop)

    try:
        runner.loop.run_until_complete(runner.connect())
        runner.loop.run_until_complete(runner.process_messages())
        runner.loop.run_forever()
    except KeyboardInterrupt:
        runner.logger.info("process interrupted")
    finally:
        runner.loop.run_until_complete(runner.stop())
        runner.logger.info("closing loop")
        runner.loop.close()
