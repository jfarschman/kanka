# kanka
Thing's I've done with Kanka.

* Kanka_converter.py - takes the output of a kanka export and turns it into a small set of files suitable for NotebookLM.

To run this, you'll need to add in a beautifulsoup4 to help parse the data.  The commands are something like this:

1. Create the file on your desktop
2. Edit the "INPUT DIRECTORY" to where your files downloaded.
3. chmod +x kanka_converter.py
4. pip install beautifulsoup4
5. python3 kanka_converter.py

I'm running this on a Mac, so YMMV.
