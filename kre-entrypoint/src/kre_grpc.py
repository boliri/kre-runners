import abc
from types import coroutine
from datetime import datetime
import gzip
import traceback
import uuid
import json

from grpclib.server import Stream
from grpclib import GRPCError
from grpclib.const import Status
from nats.js.api import ConsumerConfig, DeliverPolicy
from nats.aio.client import Client as NATS

from kre_nats_msg_pb2 import KreNatsMessage
from kre_measurements import KreMeasurements

COMPRESS_LEVEL = 9
MESSAGE_THRESHOLD = 1024 * 1024
GZIP_HEADER = b'\x1f\x8b'


# NOTE: EntrypointKRE will be extended by Entrypoint class auto-generated
class EntrypointKRE:
    def __init__(self, logger, subjects, config):
        self.logger = logger
        self.nc = NATS()
        self.js = None
        self.subscriptions = {}
        self.streams = {}
        self.subjects = subjects
        self.config = config

    @abc.abstractmethod
    def make_response_object(self, subject, response):
        # To be implemented on autogenerated entrypoint
        pass

    async def stop(self):
        """
        Stop the Entrypoint service by closing the NATS connection
        """
        if not self.nc.is_closed:
            self.logger.info("closing NATS connection")
            await self.nc.close()

    async def start(self):
        """
        Starts the entrypoint service by connecting to the NATS server and subscribing to the
        subjects related to each workflow exposed by the Entrypoint.
        """

        with open(self.config.nats_subjects_file, 'r') as f:
            subjects = json.load(f)

        self.logger.info(f"Connecting to NATS {self.config.nats_server} "
                         f"with runner name {self.config.runner_name}...")
        await self.nc.connect(self.config.nats_server, name=self.config.runner_name)
        self.js = self.nc.jetstream()

        for workflow, _ in subjects.items():
            stream = f"{self.config.runtime_id}-{self.config.krt_version_id}-{workflow}"
            subjects = [f"{stream}.entrypoint", f"{stream}.node-a"]
            input_subject = f"{stream}.{self.config.runner_name}"

            await self.js.add_stream(name=stream, subjects=subjects)

            self.logger.info(f"Created stream {stream} and subject: {subjects}")
            self.logger.info(f"Workflow: {workflow}")
            self.logger.info(f"Input subject: {input_subject}")

            self.streams[workflow] = stream
            self.subscriptions[workflow] = await self.js.subscribe(
                stream=stream,
                subject=input_subject,
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.ALL
                )
            )

    def create_kre_request_message(self, raw_msg: bytes, start: str) -> bytes:
        """
        Creates a KreNatsMessage that packages the grpc request (raw_msg) and adds the required
        info needed to send the request to the NATS server.
        It returns the message in bytes, so it can be directly sent to the NATS server.
        """
        tracking_id = str(uuid.uuid4())

        request_msg = KreNatsMessage()
        request_msg.tracking_id = tracking_id
        request_msg.payload.Pack(raw_msg)
        t = request_msg.tracking.add()
        t.node_name = self.config.runner_name
        t.start = start
        t.end = datetime.utcnow().isoformat()
        return self._prepare_nats_request(request_msg.SerializeToString())

    def create_grpc_response(self, workflow: str, message_data: bytes) -> bytes:
        """
        Creates a gRPC response from the message data received from the NATS server.
        """
        response_data = self._prepare_nats_response(message_data)
        self.logger.info(f"Received message {type(response_data)} - {response_data}")

        response_msg = KreNatsMessage()
        response_msg.ParseFromString(response_data)

        self.logger.info(f"Response message {type(response_msg)} - {response_msg}")

        if response_msg.error != "":
            self.logger.error(
                f"received error message: {response_msg.error}")

            raise GRPCError(Status.INTERNAL, response_msg.error)

        return self.make_response_object(workflow, response_msg)

    async def process_grpc_message(self, grpc_stream: Stream, workflow: str) -> None:
        """
        This function is called each time a grpc message is received.

        It processes the message by sending it by the NATS server and waits for a response.
        """
        start = datetime.utcnow().isoformat()

        try:
            grpc_raw_msg = await grpc_stream.recv_message()
            self.logger.info(f"gRPC message received {grpc_raw_msg}")

            self.logger.info(self.subjects)
            self.logger.info(self.subscriptions)
            self.logger.info(self.streams)

            # get the correct subject, subscription and stream depending on the workflow
            subject = self.subjects[workflow]
            subscription = self.subscriptions[workflow]
            stream = self.streams[workflow]

            # creates the msg to be sent to the NATS server
            request_msg = self.create_kre_request_message(grpc_raw_msg, start)

            # publish the msg to the NATS server
            self.logger.info(f"Publish to NATS subject: '{subject}' from stream: '{stream}'")
            await self.js.publish(stream=stream, subject=subject, payload=request_msg)

            # wait for the response
            self.logger.info(f"Waiting for reply message...")
            msg = await subscription.next_msg(timeout=1000)

            # prepare the grpc response message
            response = self.create_grpc_response(workflow, msg.data)

            self.logger.info(f"gRPC response: {response}")
            await grpc_stream.send_message(response)
            self.logger.info(f'gRPC successfully response')

        except Exception as err:
            err_msg = f'Exception on gRPC call : {err}'
            self.logger.error(err_msg)
            traceback.print_exc()

            if isinstance(err, GRPCError):
                raise err

    def _prepare_nats_request(self, msg: bytes) -> bytes:
        """
        Prepares the message to be sent to the NATS server by compressing it if needed.
        """
        if len(msg) <= MESSAGE_THRESHOLD:
            return msg

        out = gzip.compress(msg, compresslevel=COMPRESS_LEVEL)

        if len(out) > MESSAGE_THRESHOLD:
            raise Exception(
                "compressed message exceeds maximum size allowed of 1 MB.")

        self.logger.info(
            f"Original message size: {size_in_kb(msg)}. Compressed: {size_in_kb(out)}")

        return out

    @staticmethod
    def _prepare_nats_response(msg: bytes) -> bytes:
        if msg.startswith(GZIP_HEADER):
            return gzip.decompress(msg)

        return msg


def size_in_kb(s: bytes) -> str:
    return f"{(len(s) / 1024):.2f} KB"
