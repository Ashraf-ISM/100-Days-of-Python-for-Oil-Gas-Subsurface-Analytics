import re

with open('/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/ui/BoreholeImageAnalysis.ui', 'r') as f:
    content = f.read()

# Find <widget class=".*Layout".*> and replace with <layout class=".*Layout".*>
def replacer(match):
    return match.group(0).replace('<widget ', '<layout ')

content = re.sub(r'<widget class="[a-zA-Z]*Layout".*?>', replacer, content)
content = re.sub(r'</widget>\s*(?=</item>\s*<!--.*-->\s*<item>\s*<layout)', '</layout>', content) # wait, better to just be precise

# Just replace that specific one if it's there
with open('/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/ui/BoreholeImageAnalysis.ui', 'w') as f:
    f.write(content)
