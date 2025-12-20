# Treview

Treview is a command-line CoNLL-U to HTML converter.
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
- `--color` or `-c` can be used to specify the HTML color code to be used for the stroke and fill of the output SVG. The default is `white`, as many programmers use dark themes
- `--meta` or `m` can be followed by a space-separated list of metadata items to be displayed (if available). For example, `--meta sent_id text` makes the each sentence's ID and plain text visible above the corresponding tree

## Planned features
- [ ] display lemmas and, optionally, all other remaining fields (inlcuding ID, the most important to edit dependencies manually!)
- [ ] incorporate validation log, at least level 1 for sentences too broken to be visualized
- [x] show sentence ID (and maybe optionally other metadata?)

## Known issues
In VSCod*, treview currently only works for small files because the Document Preview extension has a hardcoded 500 ms time limit for the conversion to HTML. 

[^1]: To learn how to do that, see [this discussion thread](https://stackoverflow.com/questions/29973619/how-to-associate-a-file-extension-with-a-certain-language-in-vs-code/51228725#51228725).
