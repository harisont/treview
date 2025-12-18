#!/usr/bin/env python
import sys
from argparse import ArgumentParser, ArgumentTypeError
from itertools import chain, repeat, islice
from dataclasses import dataclass
from typing import Iterable
from drawsvg import *

from trees import read_wordlines

@dataclass
class WordLine:
    "UD wordlines with 10 named fields"
    ID: str
    FORM: str
    LEMMA: str
    POS: str
    XPOS: str
    FEATS: str
    HEAD: str
    DEPREL: str
    DEPS: str
    MISC: str

    def as_dict(self):
        return {
          'ID': self.ID, 'FORM': self.FORM, 'LEMMA': self.LEMMA,
          'POS': self.POS, 'XPOS': self.XPOS,
          'FEATS': self.FEATS, 'HEAD': self.HEAD, 'DEPREL': self.DEPREL,
          'DEPS': self.DEPS, 'MISC': self.MISC
          }
    
    def __str__(self):
        return '\t'.join(self.as_dict().values())

    def feats(self) -> dict:
        featvals = [fv.split('=') for fv in self.FEATS.split('|')]
        return {fv[0]: fv[1] for fv in featvals}

WORDLINE_FIELDS = set('ID FORM LEMMA POS XPOS FEATS HEAD DEPREL DEPS MISC'.split())

ROOT_LABEL = 'root'

def ifint(id: str) ->int:
    if id.isdigit():
        return int(id)
    else:
        return int(float(id))  # for ids like '7.1'

    
class NotValidWordLine(Exception):
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


def read_wordlines(lines):
    "read a sequence of strings as WordLines, ignoring failed ones"
    for line in lines:
        try:
            word = read_wordline(line)
            yield word
        except:
            pass

        
def ngrams(n, trees):
    "n-grams of wordlines, inside trees but not over tree boundaries"
    for tree in trees:
        wordlines = tree.wordlines()
        for i in range(len(wordlines)-n):
            yield wordlines[i:i+n] 


def wordline_ngrams(n, wordliness):
    "n-grams of wordlines, inside stanzas but not over tree boundaries"
    for wordlines in wordliness:
        for i in range(len(wordlines)-n):
            yield wordlines[i:i+n] 


def replace_by_underscores(fields, wordline):
    "replace the values of named fields by underscores"
    ldict = wordline.as_dict()
    for field in fields:
        ldict[field] = '_'
    return WordLine(**ldict)

    
def wordline_statistics(fields, wordlines):
    "frequency table of a combination of fields, as dictionary"
    stats = {}
    for word in wordlines:
        value = tuple(word.as_dict()[field] for field in fields)
        stats[value] = stats.get(value, 0) + 1
    return stats


def sorted_statistics(stats, key=lambda x: x):
    "frequency given as dict, sorted as list in descending order"
    stats = list(stats.items())
    stats.sort(key = lambda it: -key(it[1]))
    return stats


def cosine_similarity(stats1, stats2):
    "cosine similarity between two frequency dictionaries"
    dot = 0
    for k in stats1:
        dot += stats1[k] * stats2.get(k, 0)
    len1 = sum(v*v for v in stats1.values())
    len2 = sum(v*v for v in stats2.values())
    return dot/((len1 ** 0.5) * (len2 ** 0.5)) 


def wordline_ngram_statistics(fields, wordlinengrams):
    "frequency table of n-grams of field combinations"
    stats = {}
    for ngram in wordlinengrams:
        value = tuple(tuple(word.as_dict()[field] for field in fields) for word in ngram)
        stats[value] = stats.get(value, 0) + 1
    return stats


@dataclass
class Tree:
    "rose trees"
    root: object
    subtrees: list

    def prettyprint(self, level=0, indent=2):
        lines = [level*indent*' ' + str(self.root)]
        level += 1
        for tree in self.subtrees:
            lines.extend(tree.prettyprint(level))
        return lines

    def __len__(self):
        return 1 + sum(map(len, self.subtrees))

    def depth(self):
        if self.subtrees:
            return 1 + max(map(lambda t: t.depth(), self.subtrees))
        else:
            return 1


def prune_subtrees_below(tree: Tree, depth: int) -> Tree:
    "leave out parts of trees below given depth, 1 means keep root only"
    if depth <= 1:
        tree.subtrees = []
    else:
        tree.subtrees = [prune_subtrees_below(st, depth-1) for st in tree.subtrees]
    return tree
    
    
@dataclass
class DepTree(Tree):
    "depencency trees: rose trees with word lines as nodes"
    comments: list[str]
    
    def __str__(self):
        lines = self.comments
        lines.extend(self.prettyprint())
        return '\n'.join(lines)

    def wordlines(self):
        words = [self.root]
        for tree in self.subtrees:
            words.extend(tree.wordlines())
        words.sort(key=lambda w: ifint(w.ID))
        return words

    def sentence(self):
        return ' '.join([word.FORM for word in self.wordlines()])

    def prefix_comments(self, ss):
        self.comments = ss + self.comments

    def add_misc(self, s):
        self.root.MISC += '+' + s
        

    
def build_deptree(ns: list[WordLine]) -> DepTree:
    "build a dependency tree from a list of word lines"
    def build_subtree(ns, root):
        subtrees = [build_subtree(ns, n) for n in ns if n.HEAD == root.ID]
        return DepTree(root, subtrees, [])
                           
    try:
        root = [n for n in ns if n.HEAD == '0'][0]
        dt = build_subtree(ns, root)
#        if len(dt) != len(ns):   # 7.1
#            raise NotValidTree
        return dt
    except:
        raise NotValidTree(str(ns))

    
def relabel_deptree(tree: DepTree) -> DepTree:
    "set DEPREL of head to root and its HEAD to 0, renumber wordlines to 1, 2, ..."
    root = tree.root
    root.MISC = root.MISC + '('+root.DEPREL+')'
    root.DEPREL = 'root'
    words = tree.wordlines()  # sorted by ID
    numbers = {w.ID:  str(i) for w, i in zip(words, range(1, len(words) + 1))}
    numbers[root.HEAD] = '0'

    def renumber(t):
        if t.root.ID.isdigit():
            t.root.ID = numbers[t.root.ID]
        t.root.HEAD = numbers[t.root.HEAD]
        for st in t.subtrees:
            renumber(st)
        return t

    r = renumber(tree)
#    r.prefix_comments(tree.comments)
    return r


def nonprojective(tree: DepTree) -> bool:
    "if a subtree is not projective, i.e. does not span over a continuous sequence"
    ids = [int(w.ID) for w in tree.wordlines() if w.ID.isdigit()]
    ids.sort()
    return len(ids) < 1 + max(ids) - min(ids)

    
def echo_conllu_file(file: Iterable[str]):
    "reads a stream of lines, interprets them as word lines, and prints back" 
    for line in file:
        try:
            t = read_wordline(line)
            print(t)
        except:
            if not line.strip() or line.startswith('#'):
                print(line.strip())
            else:
                print('INVALID', line)

# default measures
SPACE_LEN = 15
DEFAULT_WORD_LEN = 20
CHAR_LEN = 1.8
NORMAL_TEXT_SIZE = 16
TINY_TEXT_SIZE = 10
SCALE = 5
ARC_BASE_YPOS = 30

class VisualStanza:
  """class to visualize a CoNNL-U stanza; partly corresponding to Dep in the
  Haskell implementation. 
  NOTE: unlike token IDs, positions are counted from 0, hence the -1s"""
  def __init__(self,stanza):
    wordlines = [wl for wl in read_wordlines(stanza.split("\n")) 
                 if wl.ID.isdigit()] # ignore tokens whose ID is not an int

    # token-wise info to be visualized (form + pos), cf. Dep's tokens
    self.tokens = [({"form": wl.FORM, "pos": wl.POS}) for wl in wordlines] 
      
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
      len(self.tokens[i]["form"]), 
      len(self.tokens[i]["pos"]))
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
  
  def to_svg(self):
    """generate svg tree code"""
    tokens_w = sum([self.token_width(i) for i in range(len(self.tokens))])
    spaces_w = SPACE_LEN * (len(self.tokens) - 1)

    

    # picture dimensions 
    tot_w = tokens_w + spaces_w
    tot_h = 55 + 20 * max([0] + [self.arc_height(src,trg) 
                                 for (src,trg) in self.arcs()])
    
    # otherwise everything will be mirrored
    ycorrect = lambda y: (round(tot_h)) - round(y) - 5
    svg = Drawing(tot_w,tot_h, origin=(0,0), style="background-color:white")
    
    # draw tokens (forms + pos tags)
    for (i,token) in enumerate(self.tokens):
      x = self.token_xpos(i)
      y = tot_h - 5
      svg.append(Text(token["form"], NORMAL_TEXT_SIZE, x=x, y=y))
      svg.append(Text(token["pos"], TINY_TEXT_SIZE, x=x, y=tot_h-20))

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
      arc_path = Path(stroke='black', fill='none')
      arc_path.M(x1, y1).Q(x1, y2, x2, y2).L(x3,y2).Q(x4, y2, x4, y1)
      svg.append(arc_path)

      # draw arrow
      x_arr = x + (w / 2) if trg < src else x - (w / 2)
      y_arr = ycorrect(y - 5)
      arrow = Lines(
        x_arr, y_arr, 
        x_arr - 3, y_arr - 6, 
        x_arr + 3, y_arr - 6, 
        stroke="black", fill="black", close="true")
      svg.append(arrow)

      # draw label
      x_lab = x - (len(label) * 4.5 / 2)
      y_lab = ycorrect((h / 2) + ARC_BASE_YPOS + 3)
      svg.append(Text(label, TINY_TEXT_SIZE, x=x_lab, y=y_lab))

    # draw root arrow & text
    x_root_line = self.token_xpos(self.root) + 15
    y_root_line = ycorrect(tot_h)
    root_len = tot_h - ARC_BASE_YPOS
    root_line = Line(
      x_root_line, y_root_line, 
      x_root_line, y_root_line + root_len, 
      stroke="black")
    svg.append(root_line)
    arrow_endpoint = y_root_line + root_len
    root_arrow = Lines(
      x_root_line, arrow_endpoint, 
      x_root_line - 3, arrow_endpoint - 6, 
      x_root_line + 3, arrow_endpoint - 6, 
      stroke="black", fill="black", close="true")
    svg.append(root_arrow)
    svg.append(Text(
      "root", 
      TINY_TEXT_SIZE, 
      x=x_root_line + 5, y=ycorrect(tot_h - 15)))

    return svg


def conll2svg(intxt: str) -> Iterable[str]:

    stanzas = [span for span in intxt.split("\n\n") if span.strip()]
  
    yield '<html>\n<body>\n'
    for stanza in stanzas:
        try:
          svg = VisualStanza(stanza).to_svg()
          yield svg.as_svg()
        except:
          yield "This tree cannot be visualized; check the format!"
    yield '</body>\n</html>'


if __name__ == "__main__":
    intxt = sys.stdin.read()
    for line in conll2svg(intxt):
        print(line)