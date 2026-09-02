"""Check if missing assessments exist in our database."""
import json

with open('data/assessments.json', 'r') as f:
    assessments = json.load(f)

# Check for specific slugs from train set
missing_slugs = [
    'core-java-advanced-level-new', 
    'core-java-entry-level-new', 
    'java-8-new', 
    'automata-fix-new',
    'entry-level-sales-7-1',
    'occupational-personality-questionnaire-opq32r',
    'verify-verbal-ability-next-generation',
    'administrative-professional-short-form'
]

print('Checking if train set assessments exist in our database:')
print('=' * 60)
found_count = 0
for slug in missing_slugs:
    found = [a for a in assessments if slug in a['url'].lower()]
    if found:
        print(f'FOUND: {slug}')
        print(f'       -> {found[0]["name"]}')
        found_count += 1
    else:
        print(f'MISSING: {slug}')
print(f'\nFound {found_count}/{len(missing_slugs)} assessments')

# List all Java-related assessments
print('\n' + '=' * 60)
print('All Java-related assessments in database:')
print('=' * 60)
java_assessments = [a for a in assessments if 'java' in a['name'].lower()]
for a in java_assessments:
    slug = a['url'].split('/view/')[-1].rstrip('/') if '/view/' in a['url'] else a['url']
    print(f'  {slug}: {a["name"]}')


