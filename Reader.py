#!/usr/bin/env python3

import argparse
import json
from multiprocessing import Process, Queue
import os
import queue    # needed for multiprocessing.Queue singlas
import textwrap
import tkinter as tk
import sys

from PIL import Image, ImageTk
import magic
import myougiden_api
import pyocr
import pyocr.builders

from Archive import Tree, Rar, Zip

tool = pyocr.get_available_tools()[0]
special_chars = "{}[]!\"§$%&/()\n\\.,-~\' "
colors = {'0': '#ffffff',
               '31': '#cd0000',
               '32': '#00cd00',
               '33': '#cdcd00',
               '35': '#cd00cd',
               '36': '#00cdcd'}


class Application(tk.Frame):

    def __init__(self, images, master=None):
        tk.Frame.__init__(self, master)
        self.images = images
        self.image_files = images.list()
        if os.path.isfile("last_page"):
            last_page = open("last_page", "r")
            try:
                self.last_page_json = json.load(last_page)
                self.current_page = self.last_page_json[self.images.path]
            except KeyError:
                self.last_page_json[self.images.path] = 0
                self.current_page = 0
            except:
                self.last_page_json = dict()
                self.last_page_json[self.images.path] = 0
                self.current_page = 0
            last_page.close()
        else:
            self.last_page_json = dict()
            self.last_page_json[self.images.path] = 0
            self.current_page = 0

        self.pack(fill=tk.BOTH, expand=1)
        self.createWidgets()
        self.current_page_oid = 0
        self.current_page_image = None
        self.current_page_file = None
        self.drawing_box = False
        self.box_oid = 0
        self.box_coords = (0, 0, 0, 0)
        self.lookup = None
        self.tkimage = None
        self.rotation = 0
        self.fullscreen = False
        self.text = []
        self.draw_queue = Queue()
        self.after(100, self.check_queue)

    def best_fit(self, width, height, image):
        (x, y) = image.size
        scale = width / x
        if y * scale > height:
            scale = height / y
        # print(scale)
        new_x = int(x * scale)
        new_y = int(y * scale)
        if new_x <= 0:
            new_x = 1
        if new_y <= 0:
            new_y = 1
        return image.resize((new_x, new_y), Image.BILINEAR)

    def change_image(self, amount):
        self.kill_lookup()
        new_page = self.current_page + amount
        if new_page < 0 or new_page > len(self.image_files) - 1:
            return
        self.clear_box()
        self.current_page = new_page
        self.master.title("Yurumon reader (%d/%d)" % (new_page + 1,
                                                      len(self.image_files)))
        if self.current_page_file is not None:
            self.current_page_file.close()
        self.current_page_file = self.images.open(self.image_files[new_page])
        image = Image.open(self.current_page_file)
        if self.rotation != 0:
            image = image.rotate(-90 * self.rotation)
        (width, height) = (self.frame.winfo_width(), self.frame.winfo_height())
        image = self.best_fit(width, height, image)
        self.tkimage = ImageTk.PhotoImage(image)
        self.frame.delete(self.current_page_oid)
        self.current_page_oid = self.frame.create_image(int(width/2),
                                                        int(height/2),
                                                        image=self.tkimage)
        self.current_page_image = image
        last_page = open("last_page", "w")
        self.last_page_json[self.images.path] = new_page
        json.dump(self.last_page_json, last_page)
        last_page.close()

    def check_queue(self):
        lookup = ""
        try:
            lookup = self.draw_queue.get(block=False)
        except queue.Empty:
            pass
        if lookup != "":
            self.clear_box()
            self.draw_dict(lookup)
        self.after(100, self.check_queue)

    def clear_box(self, event=None):
        self.drawing_box = False
        # if self.box_oid != 0:
        #     self.frame.delete(self.box_oid)
        self.frame.delete("text")

    def createWidgets(self):
        # self.quitButton = tk.Button(self, text='Quit',
        #                             command=self.quit)
        # self.quitButton.grid()
        self.update()
        self.frame = tk.Canvas(self, width=500,
                               height=500, cursor="tcross",
                               background="black", highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=1)
        self.frame.bind('<Left>', self.next_image)
        self.frame.bind('<Right>', self.prev_image)
        # self.frame.bind('<r>', self.rotate)
        self.frame.bind('<Configure>', self.resize_event)
        self.frame.focus_set()
        self.frame.bind('<Button-1>', self.start_drawing_box)
        self.frame.bind('<ButtonRelease-1>', self.stop_drawing_box)
        self.frame.bind('<Double-Button-1>', self.clear_box)
        self.frame.bind('<Button-2>', self.side_tap)
        self.frame.bind('<Button-3>', self.side_tap)
        self.frame.bind('<Motion>', self.draw_box)
        self.frame.bind('<F11>', self.toggle_fullscreen)

    def draw(self, string):
        self.draw_queue.put(string)

    def draw_box(self, event):
        if not self.drawing_box:
            return
        (x, y, x2, y2) = self.box_coords
        x2 = event.x
        y2 = event.y
        self.box_coords = (x, y, x2, y2)
        self.frame.delete(self.box_oid)
        self.box_oid = self.frame.create_rectangle(x, y, x2, y2,
                                                   outline="#00AA00",
                                                   fill="#00AA00",
                                                   stipple="gray50")

    def draw_dict(self, string):
        words = self.parse_color_string(string)
        self.text = []
        margin = 5
        xoff = 0
        yoff = 0
        for w in words:
            (color, text) = w
            if len(self.text) != 0:
                (x, y, x2, y2) = self.frame.bbox(self.text[-1])
                if text == "\n":
                    (a, b, c, yoff) = self.frame.bbox("text")
                    xoff = 0
                    yoff -= 1
                    text = ""
                else:
                    xoff = x2

            self.text.append(self.frame.create_text(margin + xoff,
                                                    margin + yoff, fill=color,
                                                    anchor=tk.NW, text=text,
                                                    font="14"))
            self.frame.addtag_withtag("text", self.text[-1])
        (x, y, x2, y2) = self.frame.bbox("text")
        self.textbox = self.frame.create_rectangle(x - 1, y - 1,
                                                   x2, y2, fill="black",
                                                   outline="white")
        self.frame.addtag_withtag("text", self.textbox)
        self.frame.tag_lower(self.textbox, self.text[0])

    def image_to_dict(self, image):
        bid = self.box_oid
        mode = 5
        size = image.size
        image = image.resize((size[0] * 3, size[1] * 3), Image.BICUBIC)
        if size[0] / size[1] < 1.15 and size[1] / size[0] < 1.15:
            mode = 10
        if size[0] > size[1] * 1.5:
            mode = 7
        string = self.image_to_string(image, lang="jpn",
                                      builder=pyocr.builders.TextBuilder(mode))
        string = string_filtered = "".join([c for c in string.strip()
                                            if c not in special_chars])
        self.draw("Looking up " + string)
        if string != "":
            dict_entry = myougiden_api.run(string)
        else:
            dict_entry = None
        # image.save("/tmp/export.png")
        if dict_entry is not None and string != "":
            string = dict_entry.strip("\n")
        if string == "":
            string = "Nothing recognized"
        # print(string)
        return textwrap.fill(string, 120, replace_whitespace=False,
                             drop_whitespace=False)

    def image_to_string(self, image, lang="jpn", builder=None):
        return tool.image_to_string(image, lang=lang, builder=builder)

    def kill_lookup(self):
        if self.lookup is not None and self.lookup.is_alive():
            try:
                self.lookup.terminate()
            except:
                pass
        # self.frame.delete("selection")

    def lookup_entry(self, image, coords):
        ocr_image = image.crop(coords)
        string = self.image_to_dict(ocr_image)
        if string is not None:
            self.draw(string)

    def next_image(self, event):
        self.change_image(1)

    def parse_color_string(self, string):
        escape = "\x1b"
        parts = string.split(escape)
        color_tuples = []
        new_parts = []
        for part in parts:
            if "\n" in part:
                more_parts = part.split("\n")
                for p in more_parts:
                    if p != "":
                        new_parts.append(p)
                        new_parts.append("\n")
            else:
                new_parts.append(part)
        parts = new_parts
        for part in parts:
            if part.startswith("["):
                temp = part.split("m")
                color = temp[0].strip("[")
                text = "m".join(temp[1:])
                if len(text) == 0:
                    continue
                try:
                    color_tuples.append((colors[color], text))
                except KeyError:
                    color_tuples.append((colors["0"], text))
            else:
                if len(part) == 0:
                    continue
                color_tuples.append((colors["0"], part))
        return color_tuples

    def prev_image(self, event):
        self.change_image(-1)

    def resize_event(self, event):
        self.frame.width = event.width    # >>>854
        self.frame.height = event.height  # >>>404
        self.frame.config(width=self.frame.width, height=self.frame.height)
        self.update_screen()

    def rotate(self, event):
        self.rotation = (self.rotation + 1) % 4
        self.update_screen()

    def side_tap(self, event):
        if event.x < (self.frame.winfo_width() / 2):
            self.change_image(1)
        else:
            self.change_image(-1)

    def start_drawing_box(self, event):
        self.kill_lookup()
        textbox = self.frame.bbox("text")
        selectionbox = self.frame.bbox(self.box_oid)
        for bbox in textbox, selectionbox:
            if bbox is not None:
                (x, y, x2, y2) = bbox
                mx = event.x
                my = event.y
                if mx > x and mx < x2 and my > y and my < y2:
                    self.clear_box()
                    if self.box_oid != 0:
                        self.frame.delete(self.box_oid)
                    return

        self.drawing_box = True
        x = event.x
        y = event.y
        self.box_coords = (x, y, x, y)
        if self.box_oid != 0:
            self.frame.delete(self.box_oid)
        self.box_oid = self.frame.create_rectangle(x, y, x, y,
                                                   fill="black",
                                                   stipple="gray50")
        self.frame.addtag_withtag("selection", self.box_oid)

    def stop_drawing_box(self, event):
        self.drawing_box = False
        try:
            (ix, iy, ix2, iy2) = self.frame.bbox(self.current_page_oid)
            (bx, by, bx2, by2) = self.frame.bbox(self.box_oid)
            px = (bx - ix) / (ix2 - ix)
            py = (by - iy) / (iy2 - iy)
            px2 = (bx2 - ix) / (ix2 - ix)
            py2 = (by2 - iy) / (iy2 - iy)
            # print("%f, %f, %f, %f" % (px, py, px2, py2))

            (width, height) = self.current_page_image.size
            cx = int(px * width)
            cx2 = int(px2 * width)
            cy = int(py * height)
            cy2 = int(py2 * height)
            # print("%d, %d, %d, %d" % (cx, cy, cx2, cy2))
            self.lookup = Process(target=self.lookup_entry,
                                  args=(self.current_page_image,
                                        (cx, cy, cx2, cy2)))
            # draw = ImageDraw.Draw(self.current_page_image)
            # draw.rectangle([cx, cy, cx2, cy2], outline="black")
            # ocr_image = image
            self.lookup.start()
            # self.image_to_dict(ocr_image)
        except:
            pass

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen  # Just toggling the boolean
        self.master.attributes("-fullscreen", self.fullscreen)
        self.update_screen()

    def update_screen(self):
        self.change_image(0)


def main():
    parser = argparse.ArgumentParser(description="OCR Manga Reader")
    parser.add_argument('mangafile', metavar='file', help="a .cbz/.zip, "
                        ".cbr/.rar, or directory containing your manga")
    args = parser.parse_args()
    path = args.mangafile.lower()
    filename = args.mangafile
    
    dir_check = os.path.isdir(filename)
    if dir_check:
        filetype = "Directory"

    if not dir_check:
        try:
            filetype = str(magic.from_file(filename))
        except OSError:
            print("Error: file '%s' does not exist!" % filename)
            sys.exit()

    if filetype == "Directory":
        images = Tree(args.mangafile)
    elif "Zip archive data" in filetype:
        images = Zip(args.mangafile) 
    elif "RAR archive data" in filetype:
        images = Rar(args.mangafile)
    else:
        print("Error: Unsupported filetype for '%s'\n"
              "Please specify a valid .cbz/.zip, .cbr/.rar, or directory."
              % filename)
        sys.exit()

    app = Application(images)
    app.master.title('OCR Manga Reader')
    app.update_screen()
    app.mainloop()

if __name__ == "__main__":
    main()
