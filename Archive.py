#!/usr/bin/python3

from abc import ABCMeta, abstractmethod
import rarfile
import zipfile
from io import BytesIO
import os


class Archive(metaclass=ABCMeta):
    @abstractmethod
    def list(self):
        pass

    @abstractmethod
    def open(self, filename):
        pass


def is_image(filename):
    return filename.lower().endswith("jpg") or \
        filename.lower().endswith("jpeg") or \
        filename.lower().endswith("png") or \
        filename.lower().endswith("gif")


class Rar(Archive):
    def __init__(self, filename):
        self.rar = rarfile.RarFile(filename)
        self.path = filename

    def list(self):
        return sorted([x for x in self.rar.namelist() if is_image(x)])

    def open(self, filename):
        imagefile = self.rar.open(filename)
        image = BytesIO()
        image.write(imagefile.read())
        imagefile.close()
        image.seek(0)
        return image


class Zip(Archive):
    def __init__(self, filename):
        self.zip = zipfile.ZipFile(filename)
        self.path = filename

    def list(self):
        return sorted([x for x in self.zip.namelist() if is_image(x)])

    def open(self, filename):
        imagefile = self.zip.open(filename)
        image = BytesIO()
        image.write(imagefile.read())
        image.seek(0)
        return image


class Tree(Archive):
    def __init__(self, dirname):
        self.path = dirname

    def list(self):
        return sorted([os.path.join(self.path, filename)
                       for filename in os.listdir(self.path)
                       if is_image(filename)])

    def open(self, filename):
        image = open(filename, "rb")
        return image
