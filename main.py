import schedule, requests, json, smtplib, ssl
from unidecode import unidecode
from bs4 import BeautifulSoup
from time import sleep

"""
Dated 2021-03-31:
Given the fact that my current research position is
over at the end of the summer, I need to find another
one. Funnily I've applied for two, both of which said
I am an 'ideal candidate' for various reasons, but I
emailed too late and they had already found someone
for the position. This is slightly annoying. This
program will prevent further occurrences of this.
"""

already_notified_filepath = "already_notified.json"
urop_url = "https://www.bu.edu/urop/opportunities/on-campus-research/"
target_disciplines = ["computer science", "statistics", "business", "economics"]
email_to = ["romualdo@bu.edu"]
email_from = "bot@gabrielromualdo.com"
email_from_password_filepath = "emailpwd.txt"
check_every = 15 # in minutes

already_notified = json.loads(open(already_notified_filepath).read())

def send_email(subject, contents):
	subject = unidecode(str(subject).strip())
	contents = unidecode(str(contents).strip())

	# Details
	email = "bot@gabrielromualdo.com"
	password = open(email_from_password_filepath).read().strip()

	# SSL Details
	port = 587
	servername = "smtp.dreamhost.com"

	# Create a secure SSL context
	context = ssl.create_default_context()

	# Try to log in to server and send email
	server = smtplib.SMTP(servername, port)
	server.ehlo() # Can be omitted
	server.starttls(context=context) # Secure the connection
	server.ehlo() # Can be omitted
	server.login(email, password)

	for email_address in email_to:
		server.sendmail(email, email_address, "Subject: " + subject + "\n\n" + contents)
	
	# exit server
	server.quit()

	print("\n===\n")
	print("Successfully sent email to {}".format(",".join(email_to)))
	print("\nSubject: {}".format(subject))
	print("Contents:\n{}".format(contents))

def cronjob():
	req = requests.get(urop_url)
	if(req.status_code == 200):
		try:
			html = req.text
			soup = BeautifulSoup(html, features="html.parser")
			
			# calculate target data IDs
			target_data_ids = []
			for discipline in soup.select('section.listing-discipline article'):
				discipline_name = discipline.select_one('h3').contents[0]
				if(discipline_name.lower() in target_disciplines):
					target_data_ids.append(discipline["data-id"])
			
			# get opportunities that match target data IDs
			matching_opportunities = {}
			for opportunity in soup.select('section.listing-opportunity article'):
				opportunity_disciplines_ids = opportunity["data-disciplines"].split(",")
				for discipline_id in opportunity_disciplines_ids:
					if(discipline_id in target_data_ids):
						title = opportunity.select_one('h3').contents[0]
						poster = opportunity.select_one('.connected-profile a').contents[0]
						date = opportunity.select_one('p').text.split("posted on")[1].strip()
						key = "{} by {} on {}".format(title, poster, date)
						# assumes combination of title, name, and date are unique
						# lmao if somehow the combination is not unique that would be a huge miracle
						matching_opportunities[key] = {
							"title": title,
							"poster": poster,
							"poster_url": opportunity.select_one('.connected-profile a')['href'],
							"date": date,
							"url": opportunity.select_one('a.button')['href']
						}
			
			# convert to list and notify
			matching_opportunities_list = matching_opportunities.values()
			for opportunity_key in matching_opportunities.keys():
				opportunity = matching_opportunities[opportunity_key]
				if opportunity_key not in already_notified:
					already_notified.append(opportunity_key)
					send_email("UROP: New Opportunity: {}".format(opportunity['title']), """
Title: {}
URL: {}
Date: {}
Posted By: {}, {}
""".format(opportunity['title'], opportunity['url'], opportunity['date'], opportunity['poster'], opportunity['poster_url']))
			f = open(already_notified_filepath, "w")
			f.write(json.dumps(already_notified))
			f.close()
		except Exception as e:
			print("Error: {}".format(e))
			send_email("UROP: An Error Occurred", "An error occurred with the message: {}".format(e))
	else:
		send_email("UROP: An Error Occurred Requesting Site (HTTP {})".format(req.status_code), "And that's all you need to know.")
		print("Error {}".format(req.status_code))

# create the cronjob
schedule.every(check_every).minutes.do(cronjob)

# run the cronjob
cronjob()
while True:
	schedule.run_pending()
	sleep(30) # check to run the cronjob every 30 seconds