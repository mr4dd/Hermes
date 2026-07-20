from os import walk, path

def files(directory: str) -> list:
    file_list: list = []
    extensions = ["png", "jpg", "jpeg"]
    for root, dirs, files in walk(directory):
        for file in files:
            ext = file.split(".")[-1]
            if any(e in ext for e in extensions):
                file_list.append(path.join(root, file))
    return file_list