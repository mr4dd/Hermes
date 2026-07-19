from os import walk, path

def files(directory: str) -> list:
    file_list: list = []
    for root, dirs, files in walk(directory):
        for file in files:
            file_list.append(path.join(root, file))
    return file_list

