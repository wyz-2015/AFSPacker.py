# AFSPacker.py

CRI AFS归档包打包、解包工具。[AFSPacker](https://github.com/MaikelChan/AFSPacker)的`Python 3`仿制版。

制作此版本的缘起是，原版在使用过程中出现了一个BUG，其导致重新打包的文件中，被修改过的文件丢失大量数据。本人实在不愿意在`Ubuntu`下构建`dotnet`开发环境，但是由极其需要`AFSPacker`才有的重新打包后能维持原包文件顺序的特性。故出此下策——仿制。

## 用法

与原版高度相似：

```
$ ./AFSPacker.py e [-h] AFSFilePath outDir # 解包
$ ./AFSPacker.py c [-h] inDir AFSFilePath # 创建
$ ./AFSPacker.py i [-h] AFSFilePath # 列出
```

## 依赖

库(`Ubuntu 26.04`系统源内名称)：`python3-numpy`。

## 附件

`AFS_Format_Specification.txt`：[`KIMI AI`](https://kimi.moonshot.cn/)分析原版代码得出的`CRI AFS`文件结构解析。

## LICENCE

原始程序为`Expat(MIT)`许可证。

此版本为`LGPL >= 3`许可证。

所有协议之文本收于`LICENCE.tar.xz`中。
