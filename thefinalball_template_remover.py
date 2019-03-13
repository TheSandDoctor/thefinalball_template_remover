#!/usr/bin/env python3.6
import mwclient, configparser, mwparserfromhell, re, argparse, sys
from mwclient import *
import json

def call_home(site):
    page = site.Pages['User:DeprecatedFixerBot/status']
    text = page.text()
    data = json.loads(text)["run"]["click_convert"]
    if str(data) == str(True):
        return True
    return False
def allow_bots(text, user):
    user = user.lower().strip()
    text = mwparserfromhell.parse(text)
    for tl in text.filter_templates():
        if tl.name in ('bots', 'nobots'):
            break
    else:
        return True
    for param in tl.params:
        bots = [x.lower().strip() for x in param.value.split(",")]
        if param.name == 'allow':
            if ''.join(bots) == 'none': return False
            for bot in bots:
                if bot in (user, 'all'):
                    return True
        elif param.name == 'deny':
            if ''.join(bots) == 'none': return True
            for bot in bots:
                if bot in (user, 'all'):
                    return False
    return True
def get_next_iter_item(some_iterable, window=1):
    """
    Get the item that will be in next iteration of the loop.
    This will be useful for finding {{dead link}} templates.
    This code is adapted from an answer to a StackOverflow question by user nosklo
    https://stackoverflow.com/questions/4197805/python-for-loop-look-ahead/4197869#4197869
    @param some_iterable Thing to iterate over
    @param window How far to look ahead
    """
    items, nexts = tee(some_iterable, 2)
    nexts = islice(nexts, window, None)
    return zip_longest(items, nexts)
def save_edit(page, utils, text):
     config = utils[0]
     site = utils[2]
     dry_run = utils[4]
     original_text = text

     code = mwparserfromhell.parse(text)
     for template in code.filter_templates():
         if template.name.matches("nobots") or template.name.matches("Wikipedia:Exclusion compliant"):
             if template.has("allow"):
                 if "DeprecatedFixerBot" in template.get("allow").value:
                     break # can edit
             print("\n\nPage editing blocked as template preventing edit is present.\n\n")
             return

     if not call_home(site):#config):
        raise ValueError("Kill switch on-wiki is false. Terminating program.")
     edit_summary = 'Removed deprecated parameters from [[Template:Click]] using ' +  "[[User:" + config.get('enwikidep','username') + "| " + config.get('enwikidep','username') + "]]. Mistake? [[User talk:TheSandDoctor|msg TSD!]] (please mention that this is task #1!)"
     time = 0
     while True:
         #content_changed = False
         #text = page.edit()
         #text = text.replace('[[Category:Apples]]', '[[Category:Pears]]')
         if time == 0:
             text = page.text()
         if time == 1:
        #     page = site.Pages[page.page_title]
             page.purge()
             original_text = site.Pages[page.page_title].text()
         content_changed, text = remove_deprecated_params(original_text,dry_run)
         try:
             if dry_run:
                 print("Dry run")
                 #Write out the initial input
                 text_file = open("SandInput01.txt", "w")
                 text_file.write(original_text)
                 text_file.close()
                 #Write out the output
                 if content_changed:
                     text_file = open("SandOutput01.txt", "w")
                     text_file.write(text)
                     text_file.close()
                 else:
                     print("Content not changed, don't print output")
                 break
             else:
                if verbose:
                    print("LIVE run")
                #print("Would have saved here")
                #break
                #TODO: Enable
                if not content_changed:
                    if verbose:
                        print("Content not changed, don't bother pushing edit to server")
                    break
                #break
                page.save(text, summary=edit_summary, bot=True, minor=True)
                #print(page.page_title)
                print("Saved page")
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

def remove_deprecated_params(text,dry_run):
    """
    Removes deprecated parameters from the {{Track listing}} template (and its redirects)
    @param text Page text to go over
    @param dry_run boolean Whether or not this is a dry run (dry run = no live edit)
    @returns [content_changed, content] Whether content was changed,
    (if former true, modified) content.
    """
#    print("In remove {}".format(dry_run))
    wikicode = mwparserfromhell.parse(text)
    templates = wikicode.filter_templates()
    content_changed = False

    #TODO: Testing (dry run) only
    if dry_run:
        text_file = open("SandInput.txt","w")
        text_file.write(text)
        text_file.close()
    #TODO: End dry run only

    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if (template.name.matches("click") or template.name.matches("click-fixed")):
            img = link = None
            if template.has("image") and template.has("link"):
                img = str(template.get("image").value)
                link = str(template.get("link").value)
                code.replace(template,"[[File:" + img + "|link=" + link + "]]")
                content_changed = True
            elif template.has("image"):
                img = str(template.get("image").value)
                code.replace(template,"[[File:" + img + "]]")
                content_changed = True
    return [content_changed, str(code)] # get back text to save

def main():
    limited_run = True
    pages_to_run = 1
    offset = 0
    category = True
    dry_run = False
    verbose = False

    parser = argparse.ArgumentParser(prog='DeprecatedFixerBot Tracklisting fixer', description='''Goes through pages in the category [[:Category:Pages containing click using deprecated parameters]]
    and removes deprecated parameters.''')
    parser.add_argument("-dr", "--dryrun", help="perform a dry run (don't actually edit)",
                    action="store_true")
    parser.add_argument("-v","--verbose", help="Display more information when running",
                    action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        dry_run = True
        print("Dry run")
    if args.verbose:
        print("Verbose mode")
        verbose = True
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
    utils = [config,None,site,False,dry_run]
    for page in site.Categories['Track listings with deprecated parameters']:
        if offset > 0:
            offset -= 1
            counter += 1
            print("Skipped due to offset config")
            continue
        if counter < pages_to_run:
            print("Working with: " + page.name + " Count: " + str(counter))
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
