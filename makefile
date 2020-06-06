pdf:
	pandoc --filter ./latex.py -s demand.md -o demand.docx --reference-doc=reference.docx

clean:
	rm -rf latex_images demand.docx
