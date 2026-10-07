# -*- coding: utf-8 -*-
"""dm_seg.proto 对应的 Python 消息类。

正常情况下应由 protoc 从 dm_seg.proto 生成；为免去编译环境依赖，
这里使用 protobuf 的 descriptor_pool + message_factory 在运行时构建，
效果与编译生成的 _pb2.py 等价。

如本地装有 protoc，可执行：
    protoc --python_out=. dm_seg.proto
覆盖本文件。
"""
from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message_factory as _mf

_FDP = descriptor_pb2.FileDescriptorProto()
_FDP.name = "dm_seg.proto"
_FDP.package = ""
_FDP.syntax = "proto3"

# message DanmakuElem
_elem = _FDP.message_type.add()
_elem.name = "DanmakuElem"
for _name, _num, _typ in [
    ("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_INT64),
    ("progress", 2, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
    ("mode", 3, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
    ("fontsize", 4, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
    ("color", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
    ("midHash", 6, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
    ("content", 7, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
    ("ctime", 8, descriptor_pb2.FieldDescriptorProto.TYPE_INT64),
    ("weight", 9, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
]:
    _f = _elem.field.add()
    _f.name = _name
    _f.number = _num
    _f.type = _typ
    _f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    _f.json_name = _name

# message DmSegMobileReply
_reply = _FDP.message_type.add()
_reply.name = "DmSegMobileReply"
_f = _reply.field.add()
_f.name = "elems"
_f.number = 1
_f.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
_f.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
_f.type_name = ".DanmakuElem"

_pool = descriptor_pool.Default()
_pool.Add(_FDP)

DanmakuElem = _mf.GetMessageClass(_pool.FindMessageTypeByName("DanmakuElem"))
DmSegMobileReply = _mf.GetMessageClass(_pool.FindMessageTypeByName("DmSegMobileReply"))

__all__ = ["DanmakuElem", "DmSegMobileReply"]
