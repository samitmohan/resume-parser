# import modules
import fitz
import re
from sklearn.feature_extraction.text import CountVectorizer
from fuzzywuzzy import fuzz


# no. of certification function
def extract_certifications(line):
    list_of_words = re.findall("certif", line)
    number_of_certification = len(list_of_words)
    return number_of_certification


# no. of experience extractor
def extract_experience(text):
    pattern = (
        r"(\d+|[0-9][^\s]+[a-zA-Z][^\s]+)\s*(?:year|yr|years)s?\s*(?:of\s*)?experience"
    )
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        return int(max(matches))
    else:
        return 0


# check company name for rejection of resume
def check_company_exclusion(text, excl_list, excl_comp_list):
    text_words = text.lower().split(" ")
    excl_list = list(map(lambda x: str(x).lower(), excl_list))
    excl_comp_list = list(map(lambda x: str(x).lower(), excl_comp_list))
    for i in text_words:
        if i in excl_list:
            return "Rejected"
    for i in text_words:
        if i in excl_comp_list:
            return "Rejected"
    return "Verified"


# extract raw text from resume
def extract_text(
    file_name, queue_list, custom_data_dictionary, excl_list, excl_comp_list
):
    try:
        punchuation_pattern = """!"#$%&'()*+,-/:;<=>?[\]^_`{|}~"""
        mobile_pattern = r"[\+]?[(]?[0-9]{2}[\s]?[-]?[\s]?[)]?[0-9]{8,10}"
        mail_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+"
        degree_pattern = r"\b(b\.\s*sc|bsc|b\.\s*tech|b\*s.e|diploma|btech|m\.tech|mba|phd|b\.e|m\.e|bachelor.|master of|masters|ms |b. Com)\b"

        doc = fitz.open(file_name)
        text = ""
        for page in doc:
            text += str(page.get_text())
        text_raw = text.strip()
        lines = text_raw.split("\n")
        cleaned_lines = []
        for i in lines:
            i = re.sub("[%s]" % re.escape(punchuation_pattern), "", i)
            str_en = i.strip().encode("ascii", "ignore")
            str_de = str_en.decode()
            if str_de != "":
                cleaned_lines.append(str_de.lower())

        cleaned_para = " ".join(cleaned_lines)

        mobile_matched = re.findall(mobile_pattern, cleaned_para, re.IGNORECASE)
        mail_matched = re.findall(mail_pattern, cleaned_para, re.IGNORECASE)
        mail_id = ""
        mobile_number = ""
        # find mobile no. and mail id from raw text
        if mail_matched:
            mail_id = mail_matched[0]
        if mobile_matched:
            mobile_number = mobile_matched[0]
            mobile_number = mobile_number.strip()
            mobile_number = mobile_number.replace("\n", "")
            mobile_number = mobile_number.replace(" ", "")
            if len(mobile_number) > 10:
                mobile_number = mobile_number[2:]

        # find degree matched
        degree_matched = [
            i.replace(".", "").replace(" ", "")
            for i in list(set(re.findall(degree_pattern, cleaned_para, re.IGNORECASE)))
        ]
        skills_extract = cleaned_para.lower()
        vectorizer = CountVectorizer(ngram_range=(1, 3))
        vectorizer.fit([skills_extract.lower()])
        tokens = set(vectorizer.vocabulary_.keys())
        custom_data_dictionary["Inclusion"] = custom_data_dictionary["Inclusion"].map(
            lambda x: str(x).lower()
        )
        custom_data_dictionary["Skills"] = custom_data_dictionary["Inclusion"].map(
            lambda x: ",".join([str(i) for i in x.split(",") if str(i) in tokens != -1])
        )
        custom_data_dictionary["Score"] = custom_data_dictionary["Inclusion"].map(
            lambda x: sum([1 if str(i) in tokens != -1 else 0 for i in x.split(",")])
        )

        # list of educations..
        non_tech = [
            "b.a",
            "m.a",
            "ba",
            "ma",
            "bachelor of arts",
            "master of arts",
            "master’s in business administration",
            "b. com",
            "diploma",
        ]
        bachelor = [
            "b.e",
            "b.tech",
            "btech",
            "b. tech",
            "b.s",
            "bs",
            "bachelor of engineering",
            "bsc",
            "bachelor of technology",
            "bachelor of science",
            "bachelor",
            "Bachelors of Physics",
        ]
        master = [
            "m.tech",
            "mtech",
            "master of engineering",
            "master of technology",
            "Master of Science",
            "ms",
            "m.e",
            "master",
            "MS. Quality Management Science",
            "Masters in Telecommunication",
            "Master’s in business administration",
            "pgpbm",
            "mba",
            "Mba",
        ]
        higher = ["phd"]
        degree_score = 0
        # calculation for education
        flag = 0
        for j in non_tech:
            for i in degree_matched:
                if fuzz.partial_ratio(i, j) == 100:
                    degree_score = degree_score + 10
                    flag = 1
                    break
            if flag:
                break

        flag = 0
        for j in bachelor:
            for i in degree_matched:
                if fuzz.partial_ratio(i, j) == 100:
                    degree_score = degree_score + 30
                    flag = 1
                    break
            if flag:
                break

        flag = 0
        for j in master:
            for i in degree_matched:
                if fuzz.partial_ratio(i, j) == 100:
                    degree_score = degree_score + 60
                    flag = 1
                    break
            if flag:
                break

        flag = 0
        for j in higher:
            for i in degree_matched:
                if fuzz.partial_ratio(i, j) == 100:
                    degree_score = degree_score + 90
                    flag = 1
                    break
            if flag:
                break

        no_of_certifications = extract_certifications(cleaned_para)
        experience = extract_experience(cleaned_para)
        status = check_company_exclusion(cleaned_para, excl_list, excl_comp_list)

        queue_list.append(
            [
                mail_id,
                mobile_number,
                status,
                degree_matched,
                custom_data_dictionary[["Segment", "Skills", "Score"]].to_dict(),
                degree_score,
                no_of_certifications,
                experience,
            ]
        )
    except Exception as e:
        print(e)
    return
