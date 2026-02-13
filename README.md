# Treview

Treview is a command-line CoNLL-U to HTML-embedded SVG converter.
It resues code from [deptreepy](https://github.com/aarneranta/deptreepy/), with minor modifications tailored to use inside Visual Studio Code/Codium as a CoNLL-U live previewer.

![Live treview in VSCodium](treview.gif)


## Basic usage

Using treview from the command line is simple:

1. download [`treview.py`](treview.py)
2. install its only dependency, `drawsvg`
3. make it executable (`chmod +x`) and put it somewhere in your path

You can now call treview as

```
cat YOUR-TREEBANK.conllu | treview
```

To use treview in Visual Studio Cod*, you will also need to:

1. install the [Document Preview extension](https://github.com/garlicbreadcleric/vscode-document-preview) (readily available in both VSCodium and VSCode's marketplaces)
2. open the VSCod* settings (Ctrl + ,)
3. click on Open Settings (JSON) on the top right corner (the icon is some kind of file with an arrow)
4. add something like
   ```json
    "documentPreview.converters": [
        {
            "name": "CoNLL-U",
            "fileTypes": ["tsv"],
            "command": "treview"
        }
    ]
    ```
    in the JSON itself. If you use the CoNLL-U extension, you may have to use/add a different file type. However, I strongly recommend to teach VSCode that CoNLL-U files are in fact TSVs,[^1] because if you do, you can [use Rainbow CSV to query them as a SQL database right in your editor](https://github.com/mechatroner/vscode_rainbow_csv?tab=readme-ov-file#sql-like-rbql-query-language)! How cool is that?

You can now preview open CoNLL-U files by opening the command palette (Ctrl + Shift + P) and searching for Open Document Preview.


## Optional parameters
- `--fields` or `f` can be followed by a space-separated list of CoNLL-U fields to be displayed. By default, treview displays FORM, UPOS and dependencies (HEAD + DEPREL). Supported fields: ID, FORM, LEMMA, UPOS, XPOS, HEAD (dependency edges) and DEPRELs
- `--meta` or `m` can be followed by a space-separated list of metadata items to be displayed (if available). By default, no metadata is shown
- `--color` or `-c` can be used to specify the HTML color code to be used for the stroke and fill of the output SVG. The default is `white`, as many programmers use dark themes
- `--snippets` or `-s` makes treview only produce SVG snippets without wrapping them in an HTML file, ignoring metadata. This is useful when treview is run on individual sentences to produce figures for a paper or similar, rather than used as a live previewer. 

For instance, the command I currently use for annotation in VSCodium `documentPreview.converters` is

```
treview --meta sent_id --fields id form lemma upos head deprel
```

## Known issues
In VSCod*, treview currently only works for small files because the Document Preview extension has a hardcoded 500 ms time limit for the conversion to HTML.

## Planned features
- [x] display lemmas and, optionally, (all) other remaining fields (__NOTE__: at least for the moment, I decided not to implement visualizations for FEATS, MISC and DEPREL; see above)
- [ ] incorporate validation log, at least level 1 for sentences too broken to be visualized
- [x] show sentence ID (and maybe optionally other metadata?)
- [ ] diff with another file (assumed to be with the same data but possibly different annotations) 

## Unplanned features
Some treview features have been implemented on the go for some oddly specific use cases in mind:

- if you wrap certain values in asterisks (like \*this\* or \*\*this\*\*), it will be highlighted in **bold**. This applies to:
  - FORM
  - LEMMA
  - POS (UPOS and XPOS are merged into a single SVG elements, so if you wrap either, both will be highlighted)
  - DEPREL

I hope they won't bother any other users too much.

[^1]: To learn how to do that, see [this discussion thread](https://stackoverflow.com/questions/29973619/how-to-associate-a-file-extension-with-a-certain-language-in-vs-code/51228725#51228725).
