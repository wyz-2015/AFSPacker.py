#!/usr/bin/env python3

import sys
from pathlib import Path
import json
import numpy as np
import argparse
from typing import IO
import pprint as pp
import time
import os
from enum import IntEnum

MetadataVersion = 3.1
BlockAlignmentBase = 2048


class HeaderMagicType(IntEnum):
    AFS_00 = 0
    AFS_20 = 1


class AFS_Header():
    Struct = np.dtype([
        ("magic", "S4"),
        ("entryCount", np.uint32)
    ])
    magic = {
        HeaderMagicType.AFS_00: "AFS",
        HeaderMagicType.AFS_20: "AFS "
    }
    _magic = {
        "AFS": HeaderMagicType.AFS_00,
        "AFS ": HeaderMagicType.AFS_20
    }

    def __init__(self, AFSFile: IO[bytes] = None):
        self.magicStr = ""
        self.entryCount = 0

        self.data_bin = np.zeros(1, self.Struct)[0]

        self.AFSFile = AFSFile

    def bind_AFSFile(self, AFSFile: IO[bytes]):
        self.AFSFile = AFSFile

    def read_from_dict(self, _dict: dict):
        magicStr = _dict.get("HeaderMagicType_str", None)
        self.magicStr = (self.magic[_dict["HeaderMagicType"]]
                         if (magicStr is None)
                         else magicStr)
        self.entryCount = _dict["entryCount"]

        # TODO：要是还想向下兼容原版程序的话，应该再拆分出一个build_data_bin()函数。后同
        # 目前的设计还是从dict导入后立刻通过numpy构建二进制文件数据，后同
        self.data_bin = np.array(
            (self.magicStr, self.entryCount),
            dtype=self.Struct)

    def get_dict(self) -> dict:
        return {"HeaderMagicType": self._magic[self.magicStr],
                "HeaderMagicType_str": self.magicStr,
                "entryCount": self.entryCount}

    def read_from_bin(self):
        self.data_bin = np.fromfile(self.AFSFile, self.Struct, 1)[0]

        self.magicStr = self.data_bin["magic"].decode("utf-8")
        self.entryCount = int(self.data_bin["entryCount"])

    # def write_to_bin(self):
    #    self.data_bin = np.zeros(1, dtype=self.Struct)[0]
    #    self.data_bin["magic"] = self.magicStr.encode("utf-8")
    #    self.data_bin["entryCount"] = self.entryCount
    #
    #    self.data_bin.tofile(self.AFSFile)

    def get_bin(self) -> np.void:
        return self.data_bin

    def __str__(self):
        # return "AFS_Header\n{0:s}".format(pp.pformat(
        #    {"magicStr": self.magicStr,
        #     "entryCount": self.entryCount}
        # ))
        return pp.pformat(self.get_dict())

    def __expr__(self):
        # return self.__str__()
        return str(self.data_bin)


class AttributesInfoType(IntEnum):
    InfoAtBeginning = 1
    InfoAtEnd = 2
    NoAttributes = 0


class AFS_Attributes_Header():
    Struct = np.dtype([
        ("attributesOffset", np.uint32),
        ("attributesSize", np.uint32)
    ])

    type_ = {AttributesInfoType.InfoAtBeginning: "InfoAtBeginning",
             AttributesInfoType.InfoAtEnd: "InfoAtEnd",
             AttributesInfoType.NoAttributes: "NoAttributes"
             }
    _type = {v: k for (k, v) in type_.items()}

    def __init__(self, AFSFile: IO[bytes] = None):
        self.AFSFile = AFSFile

        self.data_bin = np.zeros(1, self.Struct)[0]

        self.attributesOffset = 0
        self.attributesSize = 0

        self.headerType = 0

    def bind_AFSFile(self, AFSFile: IO[bytes]):
        self.AFSFile = AFSFile

    def read_from_dict(self, _dict: dict):
        self.attributesSize = _dict["attributesSize"]
        self.attributesOffset = _dict["attributesOffset"]
        headerType_str = _dict.get("AttributesInfoType_str", None)
        self.headerType = (_dict["AttributesInfoType"]
                           if (headerType_str is None)
                           else self._type[headerType_str])

        self.data_bin = np.array(
            (self.attributesOffset, self.attributesSize),
            dtype=self.Struct)

    def get_dict(self) -> dict:
        return {"AttributesInfoType": self.headerType,
                "AttributesInfoType_str": self.type_[self.headerType],
                "attributesOffset": self.attributesOffset,
                "attributesSize": self.attributesSize}

    def read_from_bin(self):
        self.data_bin = np.fromfile(self.AFSFile, self.Struct, 1)[0]
        (self.attributesOffset, self.attributesSize) = self.data_bin.tolist()

    # def write_to_bin(self):
    #    self.data_bin = np.array(
    #        (self.attributesOffset, self.attributesSize), dtype=self.Struct)[0]
    #    self.data_bin.tofile(self.AFSFile)
    def get_bin(self) -> np.void:
        return self.data_bin


class Entry():
    Struct_EntryInfo = np.dtype([
        ("offset", np.uint32),
        ("size", np.uint32)
    ])

    Struct_Time = np.dtype([
        ("year", np.uint16),
        ("month", np.uint16),
        ("day", np.uint16),
        ("hour", np.uint16),
        ("minute", np.uint16),
        ("second", np.uint16)
    ])
    Struct_AttributeInfo = np.dtype([
        ("name", "S32"),
        ("time", Struct_Time),
        ("customData", np.uint32)
    ])

    def __init__(self, AFSFile: IO[bytes] = None):
        self.AFSOffset = 0
        self.size = 0

        self.fileID = 0  # 在没有name，即没有attibute info时，需要用fileID作文件名
        self.name = ""
        self.mtime = tuple()
        self.customData = 0
        self.isNullEntry = False

        self.AFSFile = AFSFile

        self.entryInfo_bin = np.zeros(1, dtype=self.Struct_EntryInfo)[0]
        self.attributeInfo_bin = np.zeros(
            1, dtype=self.Struct_AttributeInfo)[0]

    def bind_AFSFile(self, AFSFile: IO[bytes]):
        self.AFSFile = AFSFile

    def is_null_entry(self):
        return (self.AFSOffset == 0 and self.size == 0)

    def get_entryinfo_bin(self) -> np.void:
        return self.entryInfo_bin

    def read_entryinfo_from_bin(self):
        self.entryInfo_bin = np.fromfile(
            self.AFSFile, self.Struct_EntryInfo, 1)[0]

        (self.AFSOffset, self.size) = self.entryInfo_bin.tolist()
        self.isNullEntry = self.is_null_entry()

    def get_entryinfo_dict(self) -> dict:
        return {"offset": self.AFSOffset,
                "size": self.size,
                "IsNull": self.isNullEntry}

    def read_entryinfo_from_dict(self, _dict_entry: dict):
        (self.AFSOffset, self.size) = (
            _dict_entry["offset"], _dict_entry["size"])
        self.entryInfo_bin = np.array(
            (self.AFSOffset, self.size),
            dtype=self.Struct_EntryInfo)

        isNull = _dict_entry.get("IsNull", None)
        self.isNullEntry = (_dict_entry["IsNull"]
                            if (isNull is not None)
                            else self.is_null_entry())

    def get_attribute_info_bin(self) -> np.void:
        # np.array(
        #        (self.name.encode("utf-8"), self.time[:6], self.customData),
        #    dtype=self.Struct_AttributeInfo)[0].tofile(self.AFSFile)
        return self.attributeInfo_bin

    def read_attribute_info_from_bin(self):
        data_bin = np.fromfile(self.AFSFile, self.Struct_AttributeInfo, 1)[0]
        self.name = data_bin["name"].decode("utf-8")
        self.mtime = data_bin["time"].tolist()
        self.customData = int(data_bin["customData"])

        self.attributeInfo_bin = data_bin

    def get_attribute_info_dict(self) -> dict:
        return {"IsNull": self.is_null_entry(),
                "Name": (self.name if (self.name) else "{0:08n}".format(self.fileID)),
                "FileName": (self.name if (self.name) else "{0:08n}".format(self.fileID)),
                # "Size": self.size,
                "CustomData": self.customData,
                "MTime": self.mtime,
                }

    def read_attribute_info_from_dict(self, _dict_attr: dict):
        # self.isNullEntry = _dict_attr["IsNull"]
        self.name = _dict_attr["Name"]
        self.customData = _dict_attr["CustomData"]

        self.attributeInfo_bin["customData"] = self.customData
        self.attributeInfo_bin["name"] = self.name.encode("utf-8")

    def update(self, inDir: Path):
        """
        根据文件实际情况更新部分数据
        """
        inFilePath = inDir / self.name
        self.mtime = time.localtime(inFilePath.stat().st_mtime)
        self.size = inFilePath.stat().st_size

        self.entryInfo_bin["size"] = self.size
        self.attributeInfo_bin["time"] = np.array(
            self.mtime[:6], dtype=self.Struct_Time)

    def extract_file(self, outDir: Path):
        outFilePath = outDir / (self.name if (self.name)
                                else "{0:08n}".format(self.fileID))
        outFile = open(outFilePath, "wb")

        posBackup = self.AFSFile.tell()

        self.AFSFile.seek(self.AFSOffset, 0)
        outFile.write(self.AFSFile.read(self.size))
        outFile.close()

        self.AFSFile.seek(posBackup, 0)

        if (self.name):  # 有属性信息时才需要导出mtime
            mtime = tuple(list(self.mtime) + 3 * [0])
            os.utime(outFilePath, times=(time.time(), time.mktime(mtime)))

    def set_fileID(self, i: int):
        self.fileID = i


class AFS():
    def __init__(self, args: argparse.Namespace):
        self.metadata = {"MetadataVersion": MetadataVersion}

        self.args = args
        self.AFSFile = open(self.args.AFSFilePath,
                            ("wb+" if (self.args.mode == "c") else "rb")
                            )

        match (self.args.mode):
            case "e":
                self.jsonFilePath = self.args.outDir / \
                    "{0}.json".format(self.args.AFSFilePath.stem)
            case "c":
                self.jsonFilePath = self.args.inDir / \
                    "{0}.json".format(self.args.AFSFilePath.stem)

        self.header = AFS_Header()
        self.attributesHeader = AFS_Attributes_Header()
        self.entries: list[Entry] = []

        self.EntryBlockAlignment = 2048
        self.metadata["EntryBlockAlignment"] = self.EntryBlockAlignment
        self.entryBlockStartOffset = 0
        self.attributesHeader_offset = 0

    def __calc_EntryBlockAlignment_from_bin__(self):
        endInfoBlock = self.AFSFile.tell() + self.attributesHeader.Struct.itemsize

        for entry in self.entries:
            if (not entry.is_null_entry()):
                self.entryBlockStartOffset = entry.AFSOffset
                break

        while (endInfoBlock + self.EntryBlockAlignment < self.entryBlockStartOffset):
            self.EntryBlockAlignment *= 2

        self.metadata["EntryBlockAlignment"] = self.EntryBlockAlignment

    def __find_attibutes_header__(self):
        # (attributesOffset, attributesSize) = np.fromfile(self.AFSFile, dtype=self.attributesHeader.Struct, 1)[0]
        self.attributesHeader.read_from_bin()

        if (self.attributesHeader.attributesOffset and self.attributesHeader.attributesSize):
            self.attributesHeader.headerType = AttributesInfoType.InfoAtBeginning
        else:
            posBackup = self.AFSFile.tell()
            self.AFSFile.seek(
                (self.entryBlockStartOffset - self.attributesHeader.Struct.itemsize),
                0)

            # (attributesOffset, attributesSize) = np.fromfile(self.AFSFile, dtype=self.attributesHeader.Struct, 1)[0]
            self.attributesHeader.read_from_bin()

            if (self.attributesHeader.attributesOffset and self.attributesHeader.attributesSize):
                self.attributesHeader.headerType = AttributesInfoType.InfoAtEnd
            else:
                self.attributesHeader.headerType = AttributesInfoType.NoAttributes

            self.AFSFile.seek(posBackup, 0)

        self.metadata.update(self.attributesHeader.get_dict())

    def read(self):
        self.AFSFile.seek(0, 0)
        self.header.bind_AFSFile(self.AFSFile)
        self.header.read_from_bin()
        self.metadata.update(self.header.get_dict())

        # 读头
        if (self.header.magicStr not in self.header._magic):
            raise ValueError("不正确的魔术字：{0:s}".format(self.header.magicStr))

        for i in range(self.header.entryCount):
            entry = Entry(self.AFSFile)
            entry.read_entryinfo_from_bin()  # 读EntryInfo表
            entry.set_fileID(i)

            self.entries.append(entry)

        # 这种形式的函数更像C的宏展开
        self.__calc_EntryBlockAlignment_from_bin__()  # 推算EntryBlockAlignment

        self.attributesHeader.bind_AFSFile(self.AFSFile)
        self.__find_attibutes_header__()  # 寻找AttributesInfo表的头

        self.metadata["Entries"] = []

        # 读AttributesInfo表
        if (self.attributesHeader.headerType != AttributesInfoType.NoAttributes):
            self.AFSFile.seek(self.attributesHeader.attributesOffset, 0)
            for entry in self.entries:
                entry.read_attribute_info_from_bin()

        for entry in self.entries:
            entryMetadata = entry.get_entryinfo_dict()
            if (self.attributesHeader.headerType != AttributesInfoType.NoAttributes):
                entryMetadata.update(entry.get_attribute_info_dict())
            self.metadata["Entries"].append(entryMetadata)

            if (self.args.mode == "e"):
                entry.extract_file(self.args.outDir)

        match (self.args.mode):
            case "i":  # i模式则打印元数据
                pp.pprint(self.metadata)
            case "e":  # e模式则转储元数据至json
                jsonFile = open(self.jsonFilePath, "wt")
                json.dump(self.metadata, jsonFile,
                          ensure_ascii=False, indent='\t')
                jsonFile.close()

    def __calc_entryBlockStartOffset__(self):
        while (self.header.Struct.itemsize + len(self.entries) * Entry.Struct_EntryInfo.itemsize + self.attributesHeader.Struct.itemsize > self.entryBlockStartOffset):
            self.entryBlockStartOffset += self.EntryBlockAlignment

    def __calc_attributes_header_offset__(self):
        match (self.attributesHeader.headerType):
            case AttributesInfoType.InfoAtBeginning:
                self.attributesHeader_offset = self.header.Struct.itemsize + \
                    len(self.entries) * Entry.Struct_EntryInfo.itemsize
            case AttributesInfoType.InfoAtEnd:
                self.attributesHeader_offset = self.entryBlockStartOffset - \
                    self.attributesHeader.Struct.itemsize

    def __calc_attributes_offset__(self):
        """
        既计算属性表的开头，同时也是文件内容区的结尾
        """
        self.attributesHeader.attributesOffset = self.entryBlockStartOffset
        self.attributesHeader.attributesSize = 0
        for entry in self.entries:
            if (not entry.isNullEntry):
                self.attributesHeader.attributesOffset += (entry.size // BlockAlignmentBase + (
                    1 if (entry.size % BlockAlignmentBase) else 0)) * BlockAlignmentBase

                self.attributesHeader.attributesSize += Entry.Struct_AttributeInfo.itemsize

    def __calc_entry_offset__(self):
        offset = self.entryBlockStartOffset
        for entry in self.entries:
            if (not entry.isNullEntry):
                entry.AFSOffset = offset

                offset += (entry.size // BlockAlignmentBase + (1 if (entry.size %
                           BlockAlignmentBase) else 0)) * BlockAlignmentBase

    def write(self):
        jsonFile = open(self.jsonFilePath, "rt")
        self.metadata = json.load(jsonFile)
        jsonFile.close()

        self.header.read_from_dict(self.metadata)

        self.attributesHeader = AFS_Attributes_Header()
        self.attributesHeader.read_from_dict(self.metadata)

        for entryMetadata in self.metadata["Entries"]:
            entry = Entry()
            entry.read_entryinfo_from_dict(entryMetadata)
            entry.read_attribute_info_from_dict(entryMetadata)
            entry.update(self.args.inDir)
            self.entries.append(entry)

        # 计算偏移，先算好偏移再填数据
        self.__calc_entryBlockStartOffset__()  # 计算首个非空Entry的起始偏移
        if (self.attributesHeader.headerType != AttributesInfoType.NoAttributes):
            self.__calc_attributes_header_offset__()  # 计算AttributesInfo表头的位置
        self.__calc_attributes_offset__()  # 计算AttributesInfo表的起始偏移

        self.__calc_entry_offset__()  # 计算各Entry文件内容的偏移

        # 写文件
        np.zeros(self.entryBlockStartOffset,
                 dtype=np.uint8).tofile(self.AFSFile)
        self.AFSFile.seek(0, 0)
        self.header.get_bin().tofile(self.AFSFile)
        np.array([entry.get_entryinfo_bin() for entry in self.entries],
                 dtype=Entry.Struct_EntryInfo).tofile(self.AFSFile)

        if (self.attributesHeader.headerType != AttributesInfoType.NoAttributes):
            self.AFSFile.seek(self.attributesHeader_offset, 0)
            self.attributesHeader.get_bin().tofile(self.AFSFile)

        self.AFSFile.seek(0, 2)
        np.zeros(self.attributesHeader.attributesOffset -
                 self.entryBlockStartOffset, dtype=np.uint8).tofile(self.AFSFile)

        for entry in self.entries:
            if (not entry.isNullEntry):
                self.AFSFile.seek(entry.AFSOffset, 0)

                file = open(self.args.inDir / entry.name, "rb")
                self.AFSFile.write(file.read())
                file.close()

        if (self.attributesHeader.headerType != AttributesInfoType.NoAttributes):  # 写属性表
            self.AFSFile.seek(self.attributesHeader.attributesOffset, 0)
            np.array([entry.get_attribute_info_bin() for entry in self.entries if (
                not entry.isNullEntry)], dtype=Entry.Struct_AttributeInfo).tofile(self.AFSFile)
            currentPos = self.AFSFile.tell()
            endPos = (currentPos // BlockAlignmentBase + (1 if (currentPos %
                      BlockAlignmentBase) else 0)) * BlockAlignmentBase
            np.zeros(endPos - currentPos, dtype=np.uint8).tofile(self.AFSFile)

    def clear(self):
        if (not self.AFSFile.closed):
            self.AFSFile.close()


def main():
    cmdParser = argparse.ArgumentParser(description="CRI AFS归档包打包、解包工具")
    modeParser = cmdParser.add_subparsers(dest="mode", help="使用模式")

    cParser = modeParser.add_parser("c", help="创建模式")
    cParser.add_argument("inDir", type=Path, help="待打包文件所在路径(需要包含对应json元数据文件)")
    cParser.add_argument("AFSFilePath", type=Path, help="AFS文件保存路径")

    iParser = modeParser.add_parser("i", help="列出模式")
    iParser.add_argument("AFSFilePath", type=Path, help="传入AFS文件路径")

    eParser = modeParser.add_parser("e", help="解包模式")
    eParser.add_argument("AFSFilePath", type=Path, help="传入AFS文件路径")
    eParser.add_argument("outDir", type=Path, help="解出文件保存路径")

    args = cmdParser.parse_args()
    print(args)
    if (args.mode is None):
        cmdParser.print_help()
        raise ValueError("未指定使用模式")

    afs = AFS(args)
    match (args.mode):
        case "i" | "e":
            afs.read()
        case "c":
            afs.write()

    afs.clear()


if (__name__ == "__main__"):
    sys.exit(main())
