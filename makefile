pdf: env
	pandoc --filter ./latex.py -s example.md -o example.docx --reference-doc=resources/template.docx

env:
	virtualenv -p python3 env
	env/bin/pip install --upgrade pip
	env/bin/pip install -r requirements.txt

clean:
	rm -rf .latex_images *.docx

purge: clean
	-@rm -rf env
