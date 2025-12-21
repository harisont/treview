#!/usr/bin/env python
import sys
import argparse
from argparse import ArgumentParser, ArgumentTypeError
from itertools import chain, repeat, islice
from dataclasses import dataclass
from typing import Iterable
from drawsvg import *

@dataclass
class MetaLine:
    "Metadata lines (key-val pairs)"
    key: str
    val: str

@dataclass
class WordLine:
    "UD wordlines with 10 named fields"
    ID: str
    FORM: str
    LEMMA: str
    UPOS: str
    XPOS: str
    FEATS: str
    HEAD: str
    DEPREL: str
    DEPS: str
    MISC: str

    def as_dict(self):
        return {
          'ID': self.ID, 'FORM': self.FORM, 'LEMMA': self.LEMMA,
          'UPOS': self.POS, 'XPOS': self.XPOS,
          'FEATS': self.FEATS, 'HEAD': self.HEAD, 'DEPREL': self.DEPREL,
          'DEPS': self.DEPS, 'MISC': self.MISC
          }
    
    def __str__(self):
        return '\t'.join(self.as_dict().values())

    def feats(self) -> dict:
        featvals = [fv.split('=') for fv in self.FEATS.split('|')]
        return {fv[0]: fv[1] for fv in featvals}

STD_FIELDS = set('ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC'.split())
DEFAULT_FIELDS = ["FORM", "UPOS", "HEAD", "DEPREL"]
SUPPORTED_FIELDS = DEFAULT_FIELDS + ["ID", "LEMMA", "XPOS"]

ROOT_LABEL = 'root'

def ifint(id: str) ->int:
    if id.isdigit():
        return int(id)
    else:
        return int(float(id))  # for ids like '7.1'

    
class NotValidWordLine(Exception):
    pass

class NotValidMetaLine(Exception):
    pass


class NotValidTree(Exception):
    pass


def read_wordline(s: str) -> WordLine:
    "read a string as a WordLine, fail if not valid"
    fields = s.strip().split('\t')
    if len(fields) == 10 and fields[0][0].isdigit():
        return WordLine(*fields)
    else:
        raise NotValidWordLine

def read_metaline(s: str) -> MetaLine:
  if s.startswith("#") and "=" in s:
      [key,val] = s[1:].split("=", maxsplit=1)
      return MetaLine(key.strip(), val.strip())
  else:
      raise NotValidMetaLine


def read_lines(lines):
    "read a sequence of strings as WordLines or MetaLines, ignoring failed ones"
    for line in lines:
        try:
            word = read_wordline(line)
            yield word
        except NotValidWordLine:
            try:
                meta = read_metaline(line)
                yield meta
            except NotValidMetaLine:
                pass

# default measures
SPACE_LEN = 15
DEFAULT_WORD_LEN = 20
CHAR_LEN = 1.8
NORMAL_TXT_SIZE = 16
SMALL_TXT_SIZE = 12
TINY_TXT_SIZE = 10
SCALE = 5
ARC_BASE_YPOS = 50

class VisualStanza:
  """class to visualize a CoNNL-U stanza; partly corresponding to Dep in the
  Haskell implementation. 
  NOTE: unlike token IDs, positions are counted from 0, hence the -1s"""
  def __init__(self, stanza, fields=DEFAULT_FIELDS):
    self.fields = fields
    lines = read_lines(stanza.split("\n"))
    wordlines = []
    self.metadict = {}
    for line in lines:
      # and: ignore tokens whose ID is not an int. We don't like them
      if type(line) == WordLine and line.ID.isdigit():
        wordlines.append(line)
      elif type(line) == MetaLine:
        self.metadict[line.key] = line.val
      else:
        pass

    # token-wise info to be visualized
    self.tokens = [({
      "ID": wl.ID,
      "FORM": wl.FORM,
      "LEMMA": wl.LEMMA,
      "UPOS": wl.UPOS, 
      "XPOS": wl.XPOS
      }) for wl in wordlines] 
      
    # list of dependency relations: [((from,to), label)], cf. Dep's deps
    self.deprels = [
      ((int(wl.ID) - 1, int(wl.HEAD) - 1), wl.DEPREL) for wl in wordlines
      if int(wl.HEAD)] # 

    # root position, cf. Dep's root
    self.root = int([wl.ID for wl in wordlines if wl.HEAD == "0"][0]) - 1
  
  def token_width(self, i):
    """total i-th token width (including space) in the output SVG"""
    abs_token_len = CHAR_LEN * max( # cf. Dep's wordLength
      0, 
      len(self.tokens[i]["FORM"]), 
      len(self.tokens[i]["LEMMA"]), 
      len(self.tokens[i]["UPOS"]) + 
      ((len(self.tokens[i]["XPOS"]) + 3) if "XPOS" in self.fields else 0))
    rel_token_len = abs_token_len / DEFAULT_WORD_LEN # cf. rwdl
    return 100 * rel_token_len + SPACE_LEN

  def token_xpos(self, i): 
    """start x coordinate of i-th token, cf. wpos"""
    return sum([self.token_width(j) for j in range(i)])
  
  def token_dist(self, a, b):
    """distance between two tokens with positions a and b"""
    return sum([self.token_width(i) for i in range(min(a, b), max(a, b))])
  
  def arcs(self):
    """helper method to extract bare arcs (pairs of positions) form deprels
    NOTE: arcs are extracted ltr, but I don't know if this is really needed"""
    return [(min(src, trg), max(src, trg)) for ((src, trg),_) in self.deprels]

  def arc_height(self, src, trg):
    """height of the arc between src and trg, cf. aheight"""

    def depth(a,b):
      # projective arcs "under" a-b
      sub_arcs = [(x,y) for (x,y) in self.arcs() 
                  if (a < x and y <= b) or (a == x and y < b)]
      if sub_arcs:
        return 1 + max([0] + [depth(x,y) for (x,y) in sub_arcs]) 
      return 0
    
    return depth(min(src,trg), max(src,trg)) + 1
  
  def to_svg(self, color="white"):
    """generate svg tree code"""
    tokens_w = sum([self.token_width(i) for i in range(len(self.tokens))])
    spaces_w = SPACE_LEN * (len(self.tokens) - 1)

    # picture dimensions 
    tot_w = tokens_w + spaces_w
    tot_h = 55 + 40 * max([0] + [self.arc_height(src,trg) 
                                 for (src,trg) in self.arcs()])
    
    # otherwise everything will be mirrored
    ycorrect = lambda y: (round(tot_h)) - round(y) - 5
    svg = Drawing(tot_w,tot_h, origin=(0,0))
    
    # draw tokens (forms + pos tags)
    for (i,token) in enumerate(self.tokens):
      x = self.token_xpos(i)
      pos = " - ".join(
        [pos for pos in [
          token["UPOS"] if "UPOS" in self.fields else None, 
          token["XPOS"] if "XPOS" in self.fields else None] 
        if pos]
      )
      if "UPOS" in self.fields or "XPOS" in self.fields:
        svg.append(
          Text(pos, TINY_TXT_SIZE, x=x, y=tot_h-40, fill=color))
      if "FORM" in self.fields:
        svg.append(
          Text(token["FORM"], NORMAL_TXT_SIZE, x=x, y=tot_h-25, fill=color))
      if "LEMMA" in self.fields:
        svg.append(
          Text(token["LEMMA"], 
          SMALL_TXT_SIZE, 
          x=x, y=tot_h-13, fill=color, font_style='italic'))
      if "ID" in self.fields:
        svg.append(
          Text(token["ID"], 
          SMALL_TXT_SIZE, 
          x=x, y=tot_h, fill=color, font_weight='bold'))


    # draw deprels (arcs + labels)
    for ((src,trg),label) in self.deprels:
      
      dxy = self.token_dist(src, trg)
      ndxy = 100 * 0.5 * self.arc_height(src,trg)
      w = dxy - (600 * 0.5) / dxy
      h = ndxy / (3 * 0.5)
      r = h / 2
      x = self.token_xpos(min(src,trg)) + (dxy/2) + (20 if trg < src else 10)
      y = ARC_BASE_YPOS
      x1 = x - w / 2
      x2 = min(x, (x1 + r))
      x4 = x + w / 2
      x3 = max(x, (x4 - r))
      y1 = ycorrect(y)
      y2 = ycorrect(y + r)

      # draw arc
      arc_path = Path(stroke=color, fill='none')
      arc_path.M(x1, y1).Q(x1, y2, x2, y2).L(x3,y2).Q(x4, y2, x4, y1)
      if "HEAD" in self.fields:
        svg.append(arc_path)

      # draw arrow
      x_arr = x + (w / 2) if trg < src else x - (w / 2)
      y_arr = ycorrect(y - 5)
      arrow = Lines(
        x_arr, y_arr, 
        x_arr - 3, y_arr - 6, 
        x_arr + 3, y_arr - 6, 
        stroke=color, fill=color, close="true")
      if "HEAD" in self.fields:
        svg.append(arrow)

      # draw label
      x_lab = x - (len(label) * 4.5 / 2)
      y_lab = ycorrect((h / 2) + ARC_BASE_YPOS + 3)
      if "DEPREL" in self.fields:
        svg.append(Text(label, TINY_TXT_SIZE, x=x_lab, y=y_lab, fill=color))

    # draw root arrow & text
    x_root_line = self.token_xpos(self.root) + 15
    y_root_line = ycorrect(tot_h)
    root_len = tot_h - ARC_BASE_YPOS
    root_line = Line(
      x_root_line, y_root_line, 
      x_root_line, y_root_line + root_len, 
      stroke=color)
    if "HEAD" in fields:
      svg.append(root_line)
      arrow_endpoint = y_root_line + root_len
      root_arrow = Lines(
        x_root_line, arrow_endpoint, 
        x_root_line - 3, arrow_endpoint - 6, 
        x_root_line + 3, arrow_endpoint - 6, 
        stroke=color, fill=color, close="true")
      svg.append(root_arrow)
    if "DEPREL" in self.fields:
      svg.append(Text(
        "root", 
        TINY_TXT_SIZE, 
        x=x_root_line + 5, y=ycorrect(tot_h - 15)))

    return svg


def conll2svg(
  intxt: str, 
  color: str="white", 
  meta: list=[], 
  fields: list=DEFAULT_FIELDS
) -> Iterable[str]:

    stanzas = [span for span in intxt.split("\n\n") if span.strip()]
  
    yield '<html>\n<body>\n'
    for stanza in stanzas:
        vstanza = VisualStanza(stanza, fields=fields)
        for item in meta:
          if item in vstanza.metadict:
            yield "<h4><b>{}</b>: {}</h4>".format(item, vstanza.metadict[item])
        yield '<div>'
        try:
          svg = vstanza.to_svg(color=color)
          yield svg.as_svg()
        except:
          yield "This tree cannot be visualized; check the format!"
        yield '</div>'
    yield '</body>\n</html>'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A CoNLL-U to HTML converter")
    parser.add_argument(
      "--fields", "-f",
      help="list of CoNLL-U fields to be displayed",
      nargs="+",
      default=DEFAULT_FIELDS
    )
    parser.add_argument(
      '--meta', '-m', 
      help='list of metadata items to be displayed, if available', 
      nargs='+', 
      default=[]
    )
    parser.add_argument(
      '--color', '-c', 
      help='HTML color code for stroke + fill', 
      default="white"
    )
    args = parser.parse_args()

    intxt = sys.stdin.read()

    fields = []
    for field in args.fields:
      field = field.upper()
      if field in STD_FIELDS:
        if field in SUPPORTED_FIELDS:
          fields.append(field)
        else:
          sys.stderr.write("Ignoring {} (field not supported)\n".format(
          field
          ))
      else:
        sys.stderr.write("Ignoring {} (not a standard CoNLL-U field)\n".format(
          field
        ))

    for line in conll2svg(
                  intxt, 
                  color=args.color, 
                  meta=args.meta,
                  fields=fields):
        print(line)