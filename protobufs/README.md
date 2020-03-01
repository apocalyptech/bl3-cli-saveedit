# Borderlands 3 `.proto`s

[protobuf](https://developers.google.com/protocol-buffers/) message definitions for Borderlands 3.

These were taken from Gibbed's Github repository here: https://github.com/gibbed/Borderlands3Protos

Many thanks to Gibbed for allowing their use in this project!

These were compiled into Python classes using the `protoc` utility, as recommended by
[Google's docs](https://developers.google.com/protocol-buffers/docs/pythontutorial):

    protoc --python_out=dest_dir *.proto

After generation, I did tweak the `import` statements slightly so they would work
inside my `bl3save` package.

