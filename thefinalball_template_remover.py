#!/usr/bin/env python3.6
import mwclient, configparser, mwparserfromhell, re, argparse, sys
from mwclient import *
import json
def getTransclusions(site,page,sleep_duration = None,extra=""):
    cont = None;
    pages = []
    i = 1
    while(1):
        result = site.api('query',list='embeddedin',eititle=str(page),eicontinue=cont,eilimit=500,format='json')
        print("got here")
        if sleep_duration is (not None):
            time.sleep(sleep_duration)
        #res2 = result['query']['embeddedin']
        for res in result['query']['embeddedin']:
            print('append ' + res['title'])
            pages.append(res['title'])
            i +=1
        try:
            cont = result['continue']['eicontinue']
            print("cont")
        except NameError:
            print("Namerror")
            return pages
        except Exception as e:
            print("Other exception" + str(e))
        #    print(pages)
            return pages

def call_home(site):
    page = site.Pages['User:DeprecatedFixerBot/status']
    text = page.text()
    data = json.loads(text)["run"]["thefinalball"]
    if str(data) == str(True):
        return True
    return False
def save_edit(page, utils, text):
     config = utils[0]
     site = utils[2]
     original_text = text

     code = mwparserfromhell.parse(text)


     if not call_home(site):#config):
        raise ValueError("Kill switch on-wiki is false. Terminating program.")
     edit_summary = 'Removed deprecated template [[Template:TheFinalBall]] using ' +  "[[User:" + config.get('enwikidep','username') + "| " + config.get('enwikidep','username') + "]]. Mistake? [[User talk:TheSandDoctor|msg TSD!]] (please mention that this is task #7!; [[Wikipedia:Bots/Requests for approval/DeprecatedFixerBot 7|BRFA in progress]])"
     time = 0
     while True:
         if time == 0:
             text = page.text()
         if time == 1:
        #     page = site.Pages[page.page_title]
             page.purge()
             original_text = site.Pages[page.page_title].text()
         content_changed, text = remove_deprecated_params(original_text)
         try:
                if not content_changed:
                    break
                page.save(text, summary=edit_summary, bot=True, minor=True)
                #print(page.page_title)
                print("Saved page")
                with open("thefinalball_saved.txt",'a+') as file:
                    file.write(str(page.page_title))
                if time == 1:
                    time = 0
                break
         except [[EditError]]:
             print("Error")
             time = 1
             time.sleep(5)   # sleep for 5 seconds, giving server some time before querying again
             continue
         except [[ProtectedPageError]] as e:
             print('Could not edit ' + page.page_title + ' due to protection')
             print(e)
         break

def remove_deprecated_params(text):
    """
    Removes deprecated parameters from the {{Track listing}} template (and its redirects)
    @param text Page text to go over
    @returns [content_changed, content] Whether content was changed,
    (if former true, modified) content.
    """
    wikicode = mwparserfromhell.parse(text)
    templates = wikicode.filter_templates()
    content_changed = False

    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if (template.name.matches("TheFinalBall") or template.name.matches("OGol")
        or template.name.matches("Ogol")
        or template.name.matches("TheFinalBall player") or template.name.matches("Zerozero")
        or template.name.matches("Zerozero profile")):
            code.remove(template)
            content_changed = True
    return [content_changed, str(code)] # get back text to save

def main():
    limited_run = True
    pages_to_run = 20
    offset = 0
    #raise ValueError("for testing, dont want whole script running")

    site = mwclient.Site(('https','en.wikipedia.org'), '/w/')
    config = configparser.RawConfigParser()
    config.read('credentials.txt')
    try:
        site.login(config.get('enwikidep','username'), config.get('enwikidep', 'password'))
    except errors.LoginError as e:
        #print(e[1]['reason'])
        print(e)
        raise ValueError("Login failed.")
    counter = 0
    utils = [config,None,site,False]
    for p in getTransclusions(site,"Template:TheFinalBall"):
        page = site.Pages[p]
        if offset > 0:
            offset -= 1
            counter += 1
            print("Skipped due to offset config")
            continue
        if counter < pages_to_run:
            print("Working with: " + page.page_title + " Count: " + str(counter))
            text = page.text()
            try:
                save_edit(page, utils, text)
            except [[EditError]]:
                print("Edit error")
                continue
            except [[ProtectedPageError]]:
                print('Could not edit ' + page.page_title + ' due to protection')
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
