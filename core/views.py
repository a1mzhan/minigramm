from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from .models import Profile, Post, Comment, Message, Notification
from .forms import SignupForm, PostForm, CommentForm, ProfileEditForm
from django.contrib.auth.forms import AuthenticationForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('feed')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('feed')
    else:
        form = SignupForm()
    return render(request, 'auth/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def feed(request):
    following_users = request.user.following.values_list('user', flat=True)
    posts = Post.objects.filter(
        Q(author__in=following_users) | Q(author=request.user)
    ).select_related('author', 'author__profile').prefetch_related('likes', 'comments')
    comment_form = CommentForm()
    return render(request, 'feed.html', {'posts': posts, 'comment_form': comment_form})


@login_required
def explore(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query)
        ).exclude(id=request.user.id)
        posts = Post.objects.filter(caption__icontains=query)
    else:
        users = []
        posts = Post.objects.all().select_related('author', 'author__profile').prefetch_related('likes')[:30]
    return render(request, 'explore.html', {'posts': posts, 'users': users, 'query': query})


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('feed')
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comment_form = CommentForm()
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author, sender=request.user,
                    notif_type='comment', post=post,
                    text=f'{request.user.username} прокомментировал ваш пост'
                )
            return redirect('post_detail', pk=pk)
    return render(request, 'post_detail.html', {'post': post, 'comment_form': comment_form})


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == 'POST':
        post.delete()
    return redirect('feed')


@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    posts = user.posts.all()
    is_following = profile.followers.filter(id=request.user.id).exists()
    return render(request, 'profile.html', {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'is_following': is_following,
    })


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = request.POST.get('display_name', '')
            request.user.save()
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        if post.author != request.user:
            Notification.objects.get_or_create(
                recipient=post.author, sender=request.user,
                notif_type='like', post=post,
                defaults={'text': f'{request.user.username} оценил ваш пост'}
            )
    return JsonResponse({'liked': liked, 'count': post.likes_count()})


@login_required
@require_POST
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)
    if request.user in target_profile.followers.all():
        target_profile.followers.remove(request.user)
        following = False
    else:
        target_profile.followers.add(request.user)
        following = True
        Notification.objects.create(
            recipient=target_user, sender=request.user,
            notif_type='follow',
            text=f'{request.user.username} подписался на вас'
        )
    return JsonResponse({'following': following, 'count': target_profile.followers_count()})


@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    text = request.POST.get('text', '').strip()
    if text:
        comment = Comment.objects.create(post=post, author=request.user, text=text)
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author, sender=request.user,
                notif_type='comment', post=post,
                text=f'{request.user.username} прокомментировал ваш пост'
            )
        return JsonResponse({'success': True, 'username': request.user.username, 'text': comment.text, 'id': comment.id})
    return JsonResponse({'success': False})


@login_required
def inbox(request):
    user = request.user
    sent = Message.objects.filter(sender=user).values_list('receiver', flat=True)
    received = Message.objects.filter(receiver=user).values_list('sender', flat=True)
    partner_ids = set(list(sent) + list(received))
    conversations = []
    for pid in partner_ids:
        partner = User.objects.get(id=pid)
        last_msg = Message.objects.filter(
            Q(sender=user, receiver=partner) | Q(sender=partner, receiver=user)
        ).last()
        unread = Message.objects.filter(sender=partner, receiver=user, is_read=False).count()
        conversations.append({'partner': partner, 'last_msg': last_msg, 'unread': unread})
    conversations.sort(key=lambda x: x['last_msg'].created_at if x['last_msg'] else timezone.now(), reverse=True)
    return render(request, 'inbox.html', {'conversations': conversations})


@login_required
def chat(request, username):
    partner = get_object_or_404(User, username=username)
    if partner == request.user:
        return redirect('inbox')
    Message.objects.filter(sender=partner, receiver=request.user, is_read=False).update(is_read=True)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
    ).order_by('created_at')
    return render(request, 'chat.html', {'partner': partner, 'messages': messages})


@login_required
@require_POST
def send_message(request, username):
    partner = get_object_or_404(User, username=username)
    text = request.POST.get('text', '').strip()
    if text and partner != request.user:
        msg = Message.objects.create(sender=request.user, receiver=partner, text=text)
        Notification.objects.create(
            recipient=partner, sender=request.user,
            notif_type='message',
            text=f'{request.user.username} написал вам сообщение'
        )
        return JsonResponse({'success': True, 'id': msg.id, 'text': msg.text, 'sender': request.user.username, 'time': msg.created_at.strftime('%H:%M')})
    return JsonResponse({'success': False})


@login_required
def get_messages(request, username):
    partner = get_object_or_404(User, username=username)
    after_id = request.GET.get('after', 0)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user),
        id__gt=after_id
    ).order_by('created_at')
    messages.filter(sender=partner, receiver=request.user).update(is_read=True)
    data = [{'id': m.id, 'text': m.text, 'sender': m.sender.username, 'time': m.created_at.strftime('%H:%M'), 'is_me': m.sender == request.user} for m in messages]
    return JsonResponse({'messages': data})


@login_required
def notifications(request):
    notifs = request.user.notifications.all()[:50]
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifs': notifs})


@login_required
def get_notifications_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    unread_msgs = Message.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'count': count, 'messages': unread_msgs})