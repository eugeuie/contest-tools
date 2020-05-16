from contests.models import Course, Contest, Problem
from accounts.models import Account, Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from datetime import datetime
import bbcode
import json
import os
from contest.settings import BASE_DIR


ACCOUNTS_PATH = 'additional_tools/accounts_new.json'
COMMENTS_PATH = 'additional_tools/comments_new.json'



def get_identifiers_json():
    identifiers = list()
    for course in Course.objects.all():
        identifiers.append({
            'type': 1,
            'id_in_contest': course.id,
            'name': course.title
        })
    for contest in Contest.objects.all():
        identifiers.append({
            'type': 2,
            'id_in_contest': contest.id,
            'name': contest.course.title + '>>>' + contest.title
        })
    for problem in Problem.objects.all():
        identifiers.append({
            'type': 3,
            'id_in_contest': problem.id,
            'name': problem.contest.course.title + '>>>' + problem.contest.title + '>>>' + problem.title
        })
    s = json.dumps(identifiers)
    with open('_identifiers.json', 'w') as file:
        file.write(s)


def create_accounts():
    s = str()
    with open('users.json') as file:
        for line in file:
            s += line
    users = json.loads(s)
    accounts = list()
    for forum_user in users:
        contest_user = User.objects.create_user(
            username=forum_user['username'],
            password=User.objects.make_random_password(),
            first_name=forum_user['first_name'],
            last_name=forum_user['last_name'],
            email=forum_user['email']
        )
        accounts.append(Account(
            user_id=contest_user.id,
            old_id=forum_user['old_id'],
            enrolled=False,
            graduated=True,
            level=8,
            admission_year=forum_user['admission_year']
        ))
    Account.objects.bulk_create(accounts)


def create_comments():
    s = str()
    with open('comments.json') as file:
        for line in file:
            s += line
    forum_comments = json.loads(s)
    comments = list()
    for forum_comment in forum_comments:
        if forum_comment['object_type'] == 1:
            object_type = ContentType.objects.get(model='Course')
        elif forum_comment['object_type'] == 2:
            object_type = ContentType.objects.get(model='Contest')
        else:
            object_type = ContentType.objects.get(model='Problem')
        comments.append(Comment(
            old_id=forum_comment['old_id'],
            author=Account.objects.get(old_id=forum_comment['author']).user,
            order=forum_comment['date_created'],
            parent_id=forum_comment['parent_id'],
            object_type=object_type,
            object_id=forum_comment['object_id'],
            text=forum_comment['text'],
            date_created=make_aware(datetime.fromtimestamp(forum_comment['date_created']))
        ))
    Comment.objects.bulk_create(comments)


def update_comments():
    comments = Comment.objects.all()
    for comment in comments:
        comment.thread_id = Comment.objects.get(old_id=comment.parent_id).id
        comment.parent_id = Comment.objects.get(old_id=comment.parent_id).id
        if comment.id != comment.parent_id:
            comment.level = 2
            comment.order = comment.order - Comment.objects.get(id=comment.parent_id).order + 1
    for comment in comments:
        if comment.id == comment.parent_id:
            comment.order = 1
    Comment.objects.bulk_update(comments, ['thread_id', 'parent_id', 'order', 'level'])


def comments_bbcode_to_html_convert():
    def render_table_tags(tag_name, value, options, parent, context):
        return f'<{tag_name}>{value}</{tag_name}>'
    parser = bbcode.Parser()
    parser.newline = ''
    parser.add_formatter('table', render_table_tags)
    parser.add_formatter('tr', render_table_tags)
    parser.add_formatter('td', render_table_tags)
    parser.drop_unrecognized = False
    comments = Comment.objects.all()
    for comment in comments:
        comment.text = parser.format(comment.text)
    Comment.objects.bulk_update(comments, ['text'])


def comments_encoding_convert():
    comments = Comment.objects.all()
    for comment in comments:
        comment.text = comment.text.replace(r'&quot;', '"')
        comment.text = comment.text.replace(r'&lt;', '<')
        comment.text = comment.text.replace(r'&gt;', '>')
        comment.text = comment.text.replace(r'&amp;', '&')
        comment.text = comment.text.replace('&nbsp;', ' ')
        comment.text = comment.text.replace('&mdash;', '—')
        comment.text = comment.text.replace('&ndash;', '–')
        comment.text = comment.text.replace('&#8230;', '…')
    Comment.objects.bulk_update(comments, ['text'])


def get_accounts_json():
    accounts = list()
    for account in Account.objects.filter(old_id__isnull=False):
        if account.old_id not in {
            2,  # Павел Алисейчик
            158,  # Юрий Шуткин
            253,  # Станислав Чиревко
            222,  # Сергей Родин
            160,  # Дмитрий Алексеев
            168,  # Кирилл Голиков
            272,  # Наталья Дейнека
            162,  # Александр Петюшко
            275,  # Руслан Бекташев
        }:
            accounts.append({
                'old_id': account.old_id,
                'username': account.username,
                'password': account.user.password,
                'first_name': account.user.first_name,
                'last_name': account.user.last_name,
                'email': account.user.email,
                'level': account.level,
                'type': account.type,
                'admission_year': account.admission_year,
                'enrolled': account.enrolled,
                'graduated': account.graduated,
            })
    s = json.dumps(accounts)
    file_path = os.path.join(BASE_DIR, ACCOUNTS_PATH)
    with open(file_path, 'w+') as file:
        file.write(s)


def get_comments_json():
    comments = list()
    for comment in Comment.objects.filter(old_id__isnull=False):
        comments.append({
            'old_id': comment.old_id,
            'author': Account.objects.get(user=comment.author).old_id,
            'thread_id': Comment.objects.get(id=comment.thread_id).old_id,
            'parent_id': Comment.objects.get(id=comment.parent_id).old_id,
            'level': comment.level,
            'order': comment.order,
            'object_type': comment.object_type.model,
            'object_id': comment.object_id,
            'text': comment.text,
            'is_deleted': comment.is_deleted,
            'date_created': [datetime.timestamp(comment.date_created), str(comment.date_created)],
        })
    comments.sort(key=lambda x: x['date_created'][0], reverse=True)
    for i in range(len(comments)):
        comments[i]['date_created'] = comments[i]['date_created'][1]
    s = json.dumps(comments)
    file_path = os.path.join(BASE_DIR, COMMENTS_PATH)
    with open(file_path, 'w+') as file:
        file.write(s)
