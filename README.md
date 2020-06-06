# Pandoc filter: markdown to google docs

`pandoc -t json -s demand.md | ./latex.py | pandoc -f json --reference-doc=reference.docx -o demand.docx`
or
`pandoc --filter ./latex.py -s demand.md -o demand.docx --reference-doc=reference.docx`

- `brew install imagemagick` to get `convert` command

## Files

- `latex.py`
    + pandoc ["filter"](https://github.com/jgm/pandocfilters) that works on the JSON representation of the pandoc AST
- `reference.docx`
    + the Word document style template. Modify in Word for different styles

## Notes

- based on [this example](https://github.com/jgm/pandocfilters/blob/master/examples/tikz.py)
- https://tex.stackexchange.com/questions/50162/how-to-make-a-standalone-document-with-one-equation
- get default pandoc reference `docx` file with
    - `pandoc --print-default-data-file reference.docx > reference.docx`
- i wonder if the `--filter` form passes the `format` through... it does!

![Screen Shot 2020-02-27 at 1.28.29 PM](/Users/ajfriend/Desktop/Screen Shot 2020-02-27 at 1.28.29 PM.png)
