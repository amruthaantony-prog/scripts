from spellchecker import SpellChecker
spell = SpellChecker(language='en')
text = "Th1s iz a tezt"
corrected_words = []
for word in text.split():
    # Only attempt correction if the word is not in the dictionary
    if word.lower() not in spell:
        suggestion = spell.correction(word)
        corrected_words.append(suggestion if suggestion else word)
    else:
        corrected_words.append(word)
corrected_text = " ".join(corrected_words)
print(corrected_text)  # "This is a text"
