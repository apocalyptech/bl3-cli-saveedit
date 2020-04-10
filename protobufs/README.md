# Borderlands 3 `.proto`s

[protobuf](https://developers.google.com/protocol-buffers/) message definitions for Borderlands 3.

These were taken from Gibbed's Github repository here: https://github.com/gibbed/Borderlands3Protos
They can also be extracted directly from `Borderlands3.exe` with
[protodec](https://github.com/schdub/protodec).  I've converted the output from that
app into protobuf v3, and done a few other formatting tweaks as well.

Many thanks to Gibbed for showing us how to get at that data!

These were compiled into Python classes using the `protoc` utility, as recommended by
[Google's docs](https://developers.google.com/protocol-buffers/docs/pythontutorial):

    protoc --python_out=../bl3save *.proto

After generation, I did tweak the `import` statements slightly so they would work
inside my `bl3save` package.

