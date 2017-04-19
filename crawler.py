# -*- coding: utf-8 -*-
import re
import string
import requests
import json
from bs4 import BeautifulSoup
from pprint import pprint
import sqlite3


POS = ['Verb', 'Substantiv']
ENG_POS = ['verb', 'noun', 'adjective']
TRANSLATIONS = ['engelska', 'ukrainska', 'ryska']
NOUN_FORMS = ['singular', 'plural', 'indefinite', 'definite']
ARTICLES = ['en', 'ett']

CONN = sqlite3.connect('ordet.db')
CURSOR = CONN.cursor()


def substantiv_forms(table):
	th = table.find('th', text='Nominativ')
	forms = {'singular': {}, 'plural': {}}
	values = []
	for sb in th.find_next_siblings():
		val = sb.string
		if val is None:
			val = sb.a.string
		values.append(val)
	for i, v in enumerate(values):
		forms[NOUN_FORMS[i // 2]][NOUN_FORMS[i % 2 + 2]] = v
	print(forms)
	if forms['singular']['definite'][-1] == 't':
		forms['article'] = 'ett'
	else:
		forms['article'] = 'en'
	insert_substantiv(forms)
	return forms


def insert_substantiv(forms):
	try:
		CURSOR.execute(u"INSERT INTO words(basic_form) VALUES (?);", (forms['singular']['indefinite'],))
		last_id = CURSOR.lastrowid
	except sqlite3.IntegrityError:
		last_id = CURSOR.execute(u"SELECT id FROM words WHERE basic_form=?", (forms['singular']['indefinite'],)).fetchone()[0]
	
	try:
		CURSOR.execute(u"INSERT INTO nouns(word_id, article, sing_definite, pl_indefinite, pl_definite) VALUES (?,?,?,?,?);",
			(last_id, forms["article"], forms['singular']['definite'], forms["plural"].get("indefinite"), forms['plural'].get('definite')))
	except sqlite3.IntegrityError: pass


def verb_forms(table):
	forms = {}
	for row in table.find_all('tr', recursive=False):
		form_name = row.find('th', recursive=False)
		if not form_name: continue
		if 'main' in form_name.get('class', []): continue
		if 'colspan' in form_name.attrs:
			if form_name.string is not None:
				forms['particip'] = {}
			continue
		form = row.td
		for el in form.contents:
			val = el.string
			if val is None:
				val = []
				for c in el.contents:
					res = c.string
					if res is not None:
						res = re.sub(r'[{} ]'.format(string.punctuation), '', res)
						if res:
							val.append(res)
				val = "|".join(val)
		if val:
			if forms.get('particip') is None:
				forms[form_name.string.lower()] = val
			else:
				forms['particip'][form_name.string.lower()] = val
	insert_verb(forms)
	return forms


def insert_verb(forms):
	try:
		CURSOR.execute(u"INSERT INTO words(basic_form) VALUES (?);", (forms['infinitiv'],))
		last_id = CURSOR.lastrowid
	except sqlite3.IntegrityError:
		last_id = CURSOR.execute(u"SELECT id FROM words WHERE basic_form=?", (forms['infinitiv'],)).fetchone()[0]
	
	try:
		CURSOR.execute(u"INSERT INTO verbs(word_id, imperativ, presens, preteritum, supinum) VALUES (?,?,?,?,?);",
			(last_id, forms["imperativ"], forms['presens'], forms['preteritum'], forms['supinum']))
	except sqlite3.IntegrityError: pass


def adjektiv_forms(table):
	pass


def translate(forms, table):
	forms['translations'] = {}
	for li in table.find_all('li'):
		concat, trans = False, li.contents
		lang = trans[0].replace(': ', '')
		if lang not in TRANSLATIONS: continue
		val = []
		for el in trans[1:]:
			if el.name == "span":
				res = el.string
				if res is not None:
					res = re.split(r'[{}]'.format(string.punctuation), res)
					if concat:
						for term in res:
							val[-1] += " " + term.strip()
						concat = False
					else:
						for term in res:
							val.append(term.strip())
			elif el.name is None and el.string == " " and val:
				concat = True
		val = "|".join(val)
		print(val)
		forms['translations'][lang] = val

	print(forms['translations'])

	trials = [forms.get('infinitiv', False), forms.get('singular', {}).get('indefinite', False)]

	for i, t in enumerate(trials):
		if t:
			basic_form, pos_id = t, i + 1
			break

	if basic_form:
		word_id = CURSOR.execute(u"SELECT id FROM words WHERE basic_form=?", (basic_form,)).fetchone()[0]
		if word_id:
			for lang in forms['translations'].keys():
				lang_id = TRANSLATIONS.index(lang) + 1
				for tr in forms['translations'][lang].split("|"):
					try:
						CURSOR.execute(u"INSERT INTO translations(language_id, word_id, pos_id, translation) VALUES (?,?,?,?);", (lang_id, word_id, pos_id, tr))
					except sqlite3.IntegrityError:
						pass

def get_words(filename):
	words = []
	with open(filename, 'r') as f:
		for line in f:
			words.append(line.strip())
	return words


def process_words(words):
	params = {
		'printable': 'yes'
	}

	results = {}

	for word in words:
		params['title'] = word
		print(word)
		info = {}
		r = requests.get('https://sv.wiktionary.org/w/index.php', params=params)
		html_response = r.content
		soup = BeautifulSoup(html_response, 'html.parser')

		start = None
		for h2 in soup.find_all('h2'):
			for c in h2.findChildren():
				if c['id'] == "Svenska":
					start = h2

		if start:
			cur_pos, cur_forms = None, None
			for sb in start.find_next_siblings():
				if sb.name == 'h2':
					break
				elif sb.name == 'h3':
					cur_pos = sb.span['id']
					print(cur_pos, cur_pos in POS)
				elif cur_pos:
					if cur_pos in POS:
						if sb.name == "table" and "grammar" in sb.get('class', []) and not info.get(cur_pos.lower(), False):
							proc = globals().get("{}_forms".format(cur_pos.lower()))
							cur_forms = proc(sb)
							info[cur_pos.lower()] = cur_forms
						if sb.name == "div" and "NavFrame" in sb.get('class', []):
							table = sb.find('table', class_="översättningar")
							if table:
								if cur_forms is None: cur_forms = {}
								translate(cur_forms, sb)
								info[cur_pos.lower()] = cur_forms
		results[word] = info
		print("{} - {}".format(word, "Done!"))
	return results


# process_words(get_words('verbs_grupp1.txt'))
# process_words(get_words('verbs_grupp2.txt'))
# process_words(get_words('nouns_group1.txt'))
# process_words(get_words('nouns_group2.txt'))
# process_words(get_words('nouns_group3.txt'))
# process_words(get_words('nouns_group4.txt'))
# process_words(get_words('nouns_group5.txt'))

process_words(["radergummi", "tidning", "gifta"])

CONN.commit()
CONN.close()