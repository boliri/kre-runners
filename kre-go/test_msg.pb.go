// Code generated by protoc-gen-go. DO NOT EDIT.
// source: test_msg.proto

package kre

import (
	fmt "fmt"
	proto "github.com/golang/protobuf/proto"
	math "math"
)

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// This is a compile-time assertion to ensure that this generated file
// is compatible with the proto package it is being compiled against.
// A compilation error at this line likely means your copy of the
// proto package needs to be updated.
const _ = proto.ProtoPackageIsVersion3 // please upgrade the proto package

type TestInput struct {
	Name                 string   `protobuf:"bytes,1,opt,name=name,proto3" json:"name,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}

func (m *TestInput) Reset()         { *m = TestInput{} }
func (m *TestInput) String() string { return proto.CompactTextString(m) }
func (*TestInput) ProtoMessage()    {}
func (*TestInput) Descriptor() ([]byte, []int) {
	return fileDescriptor_fccd8d6670148cd2, []int{0}
}

func (m *TestInput) XXX_Unmarshal(b []byte) error {
	return xxx_messageInfo_TestInput.Unmarshal(m, b)
}
func (m *TestInput) XXX_Marshal(b []byte, deterministic bool) ([]byte, error) {
	return xxx_messageInfo_TestInput.Marshal(b, m, deterministic)
}
func (m *TestInput) XXX_Merge(src proto.Message) {
	xxx_messageInfo_TestInput.Merge(m, src)
}
func (m *TestInput) XXX_Size() int {
	return xxx_messageInfo_TestInput.Size(m)
}
func (m *TestInput) XXX_DiscardUnknown() {
	xxx_messageInfo_TestInput.DiscardUnknown(m)
}

var xxx_messageInfo_TestInput proto.InternalMessageInfo

func (m *TestInput) GetName() string {
	if m != nil {
		return m.Name
	}
	return ""
}

type TestOutput struct {
	Greeting             string   `protobuf:"bytes,1,opt,name=greeting,proto3" json:"greeting,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}

func (m *TestOutput) Reset()         { *m = TestOutput{} }
func (m *TestOutput) String() string { return proto.CompactTextString(m) }
func (*TestOutput) ProtoMessage()    {}
func (*TestOutput) Descriptor() ([]byte, []int) {
	return fileDescriptor_fccd8d6670148cd2, []int{1}
}

func (m *TestOutput) XXX_Unmarshal(b []byte) error {
	return xxx_messageInfo_TestOutput.Unmarshal(m, b)
}
func (m *TestOutput) XXX_Marshal(b []byte, deterministic bool) ([]byte, error) {
	return xxx_messageInfo_TestOutput.Marshal(b, m, deterministic)
}
func (m *TestOutput) XXX_Merge(src proto.Message) {
	xxx_messageInfo_TestOutput.Merge(m, src)
}
func (m *TestOutput) XXX_Size() int {
	return xxx_messageInfo_TestOutput.Size(m)
}
func (m *TestOutput) XXX_DiscardUnknown() {
	xxx_messageInfo_TestOutput.DiscardUnknown(m)
}

var xxx_messageInfo_TestOutput proto.InternalMessageInfo

func (m *TestOutput) GetGreeting() string {
	if m != nil {
		return m.Greeting
	}
	return ""
}

func init() {
	proto.RegisterType((*TestInput)(nil), "TestInput")
	proto.RegisterType((*TestOutput)(nil), "TestOutput")
}

func init() {
	proto.RegisterFile("test_msg.proto", fileDescriptor_fccd8d6670148cd2)
}

var fileDescriptor_fccd8d6670148cd2 = []byte{
	// 107 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x09, 0x6e, 0x88, 0x02, 0xff, 0xe2, 0xe2, 0x2b, 0x49, 0x2d, 0x2e,
	0x89, 0xcf, 0x2d, 0x4e, 0xd7, 0x2b, 0x28, 0xca, 0x2f, 0xc9, 0x57, 0x92, 0xe7, 0xe2, 0x0c, 0x01,
	0x8a, 0x78, 0xe6, 0x15, 0x94, 0x96, 0x08, 0x09, 0x71, 0xb1, 0xe4, 0x25, 0xe6, 0xa6, 0x4a, 0x30,
	0x2a, 0x30, 0x6a, 0x70, 0x06, 0x81, 0xd9, 0x4a, 0x1a, 0x5c, 0x5c, 0x20, 0x05, 0xfe, 0xa5, 0x25,
	0x20, 0x15, 0x52, 0x5c, 0x1c, 0xe9, 0x45, 0xa9, 0xa9, 0x25, 0x99, 0x79, 0xe9, 0x50, 0x55, 0x70,
	0xbe, 0x13, 0x6b, 0x14, 0x73, 0x76, 0x51, 0x6a, 0x12, 0x1b, 0xd8, 0x60, 0x63, 0x40, 0x00, 0x00,
	0x00, 0xff, 0xff, 0x4b, 0x7e, 0x02, 0x45, 0x6a, 0x00, 0x00, 0x00,
}
