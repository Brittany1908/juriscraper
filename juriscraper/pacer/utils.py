import re
import requests
import tldextract


def get_pacer_court_info():
    r = requests.get("https://court-version-scraper.herokuapp.com/courts.json")
    return r.json()


def get_courts_from_json(j):
    courts = []
    for k, v in j.items():
        for court in v['courts']:
            court['type'] = k
            courts.append(court)
    return courts


def get_court_id_from_url(url):
    """Extract the court ID from the URL."""
    parts = tldextract.extract(url)
    return parts.subdomain.split('.')[1]


def get_pacer_case_id_from_docket_url(url):
    """Extract the pacer case ID from the docket URL.

    In: https://ecf.almd.uscourts.gov/cgi-bin/DktRpt.pl?56120
    Out: 56120
    In: https://ecf.azb.uscourts.gov/cgi-bin/iquery.pl?625371913403797-L_9999_1-0-663150
    Out: 663150
    """
    param = url.split('?')[1]
    if 'L' in param:
        return param.rsplit('-', 1)[1]
    return param


def get_pacer_doc_id_from_doc1_url(url):
    """Extract the pacer document ID from the doc1 URL.

    In:  https://ecf.almd.uscourts.gov/doc1/01712427473
    Out: 01712427473
    In:  /doc1/01712427473
    Out: 01712427473
    """
    return url.rsplit('/', 1)[1]


def reverse_goDLS_function(s):
    """Extract the arguments from the goDLS JavaScript function.

    In: goDLS('/doc1/01712427473','56121','69','','','1','','');return(false);
    Out: {
      'form_post_url': '/doc1/01712427473',
      'caseid': '56121',
      'de_seq_num': '69',
      'got_receipt': '',
      'pdf_header': '',
      'pdf_toggle_possible': '1',
      'magic_num': '',
      'hdr': '',
    }

    The key names correspond to the form field names in the JavaScript on PACER,
    but we don't actually know what each of these values does. Our best
    speculation is:

     - form_post_url: Where the form is posted to. The HTML 'action' attribute.
     - caseid: The internal PACER ID for the case.
     - de_seq_num: Unclear. This seems to be the internal ID for the document,
       but this field can be omitted without any known issues.
     - got_receipt: If set to '1', this will bypass the receipt page and
       immediately direct you to the page where the PDF is embedded in an
       iframe.
     - pdf_header: Can be either 1 or 2. 1: Show the header. 2: No header.
     - pdf_toggle_possible: This seems to always be 1. Could be that some courts
       do not allow the header to be turned off, but we haven't discoered that
       yet.
     - magic_num: This is used for the "One free look" downloads.
     - hdr: Unclear what HDR stands for but on items that have attachments,
       passing this parameter bypasses the download attachment screen and takes
       you directly to the PDF that you're trying to download. For an example,
       see document 108 from 1:12-cv-00102 in tnmd, which is a free opinion that
       has an attachment.
    """
    args = re.findall("\'(.*?)\'", s)
    return {
        'form_post_url': args[0],
        'caseid': args[1],
        'de_seq_num': args[2],
        'got_receipt': args[3],
        'pdf_header': args[4],
        'pdf_toggle_possible': args[5],
        'magic_num': args[6],
        'hdr': args[7],
    }


def make_doc1_url(court_id, pacer_document_number, skip_attachment_page):
    """Make a doc1 URL.

    If skip_attachment_page is True, we replace the fourth digit with a 1
    instead of a zero, which bypasses the attachment page.
    """
    if skip_attachment_page and pacer_document_number[3] == '0':
        # If the fourth digit is a 0, replace it with a 1
        pacer_document_number = pacer_document_number[:3] + '1' + \
                                pacer_document_number[4:]
    return 'https://ecf.%s.uscourts.gov/doc1/%s' % (court_id,
                                                    pacer_document_number)


def is_pdf(response):
    """Determines whether the item downloaded is a PDF or something else."""
    if response.headers.get('content-type') == 'application/pdf':
        return True
    return False
