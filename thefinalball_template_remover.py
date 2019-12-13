#!/usr/bin/env python3.6
import json
import configparser
import mwclient
import mwparserfromhell
import re
import sys
import time
from mwclient import *


def getTransclusions(site, page, sleep_duration=None):
    cont = None
    pages = []
    i = 1
    while 1:
        result = site.api('query', list='embeddedin', eititle=str(page), eicontinue=cont, eilimit=500, format='json')
        if sleep_duration is (not None):
            time.sleep(sleep_duration)
        for res in result['query']['embeddedin']:
            print('append ' + res['title'])
            pages.append(res['title'])
            i += 1
        try:
            cont = result['continue']['eicontinue']
            print('cont')
        except NameError:
            print('Namerror')
            return pages
        except Exception as e:
            print("Other exception" + str(e))
            return pages


def call_home(site):
    page = site.Pages['User:DeprecatedFixerBot/status']
    text = page.text()
    data = json.loads(text)['run']['thefinalball']
    if str(data) == str(True):
        return True
    return False


def save_edit(page, utils, text):
    config = utils[0]
    site = utils[2]
    original_text = text

    if not call_home(site):
        raise ValueError('Kill switch on-wiki is false. Terminating program.')

    edit_summary = 'Removed deprecated template [[Template:TheFinalBall]] using ' + "[[User:" + config.get('enwikidep',
                                                                                                           'username') \
                   + '| ' + config.get('enwikidep', 'username') + ']]. Mistake? [[User talk:TheSandDoctor|msg TSD!]] \
                   (please mention that this is task #7!; [[Wikipedia:Bots/Requests for approval/DeprecatedFixerBot 7|\
                   BRFA in progress]])'
    times_over = 0
    while True:
        if times_over == 1:
            page.purge()  # Time to start over, purge the page to ensure getting newest version
            original_text = site.Pages[page.page_title].text()  # Get a new copy of the article's text
        content_changed, text = remove_deprecated_params(original_text)
        try:
            if not content_changed:
                break  # Content not changed, so don't bother trying to save it/going over it
            page.save(text, summary=edit_summary, bot=True, minor=True)
            print("Saved page")

            # Write out a record that this page has been saved
            with open("thefinalball_saved.txt", 'a+') as file:
                file.write(str(page.page_title) + '\n')
            if times_over == 1:
                times_over = 0
            break
        except errors.ProtectedPageError as e:
            print('Could not edit ' + page.page_title + ' due to protection')
            print(e)
        except errors.EditError:
            print('Error')
            times_over = 1
            time.sleep(5)  # sleep for 5 seconds, giving server some time before querying again
            continue
        break


def remove_deprecated_params(text):
    """
    Removes the {{TheFinalBall}} template (and its redirects)
    @param text Page text to go over
    @returns [content_changed, content] Whether content was changed,
    (if former true, modified) content.
    """
    original_text = text
    text = re.sub(r'<ref>.*{{ogol(\s*)?(\|.*)?}}.*<\/ref>', '', string=text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'<ref>.*{{TheFinalBall(\s*)?(\|.*)?}}.*<\/ref>', '', string=text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'<ref>.*{{TheFinalBall player(\s*)?(\|.*)?}}.*<\/ref>', '', string=text,
                  flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'<ref>.*{{Zerozero(\s*)?(\|.*)?}}.*<\/ref>', '', string=text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'<ref>.*{{Zerozero profile(\s*)?(\|.*)?}}.*<\/ref>', '', string=text,
                  flags=re.IGNORECASE | re.MULTILINE)
    content_changed = original_text is not text
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if (template.name.matches('TheFinalBall') or template.name.matches('OGol')
                or template.name.matches('Ogol')
                or template.name.matches('TheFinalBall player') or template.name.matches('Zerozero')
                or template.name.matches('Zerozero profile')):
            code.remove(template)
            content_changed = True
    return [content_changed, str(code)]  # get back text to save


def main():
    # These two variables are to control how many pages are ran
    pages_to_run = 9
    offset = 0

    site = mwclient.Site(('https', 'en.wikipedia.org'), '/w/')
    config = configparser.RawConfigParser()
    config.read('credentials.txt')
    try:
        site.login(config.get('enwikidep', 'username'), config.get('enwikidep', 'password'))
    except errors.LoginError as e:
        print(e)
        raise ValueError("Login failed.")
    counter = 0
    utils = [config, None, site, False]
    for p in getTransclusions(site, 'Template:TheFinalBall'):
        page = site.Pages[p]
        if offset > 0:
            offset -= 1
            counter += 1
            print('Skipped due to offset config')
            continue
        if counter < pages_to_run:
            print('Working with: ' + page.page_title + ' Count: ' + str(counter))
            text = page.text()
            try:
                save_edit(page, utils, text)
            except errors.ProtectedPageError:
                print('Could not edit ' + page.page_title + ' due to protection')
            except errors.EditError:
                print('Edit error')
                continue
            counter += 1
        else:
            return


if __name__ == "__main__":
    try:
        verbose = False
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(0)
