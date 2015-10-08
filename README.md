# OCR-Manga
A very simplistic manga reader with integrated OCR.

## Installation

OCR-Manga has a few dependencies you will need:
- Python 3.x
- [tkinter](http://core.tcl.tk/)
  - Most distributions have tkinter available in their package repositories
- [Tesseract](https://github.com/tesseract-ocr/tesseract)
  - You will also need the [jpn data files](https://github.com/tesseract-ocr/langdata)
  - Most distributions have both Tesseract and various language data available 
    in their package repositories.
- [pillow](https://github.com/python-pillow/Pillow)
- [pyocr](https://github.com/jflesch/pyocr)
- [magic](https://github.com/ahupp/python-magic)
- [myougiden](https://github.com/leoboiko/myougiden)
- [rarfile](https://github.com/markokr/rarfile)

Ubuntu/Debian
-------------

Install pip, Tk, and Tesseract:

`sudo apt-get install python3-pip python3-tk tesseract-ocr tesseract-ocr-jpn`


Arch Linux
----------

Install pip, Tk, and Tesseract:

`sudo pacman -S python-pip tk tesseract tesseract-data-jpn`


Gentoo
------

Make sure you have `tk` in your USE flags for Python 3. You'll also need to
either have `jp` in your LINGUAS or specify `linguas_jp` as an USE flag for
Tesseract.

Install pip and Tesseract:

`sudo emerge -a dev-python/pip app-lang/tesseract`

Install various python modules:
-------------------------------

`sudo pip install pillow pyocr python-magic myougiden rarfile`

## Usage

`./Reader.py /path/to/manga`

The manga can be a zip, rar, or just a plain old directory.

## Contributions

Contributions are welcomed and accepted. It is required that all pull
requests be [PEP 0008](https://www.python.org/dev/peps/pep-0008) formatted.

## Screenshots

![Screenshot of Yurumon](http://dedi.klaxa.eu/public/yurumon_ocr.jpg)
![Screenshot of Yurumon](http://dedi.klaxa.eu/public/yurumon_ocr_color.png)
![Screenshot of Yurumon](http://dedi.klaxa.eu/public/yurumon_dark.png)

# Demos

http://dedi.klaxa.eu/public/Manga_reader_demo.mkv

http://dedi.klaxa.eu/public/Manga_reader_demo_2.mkv
