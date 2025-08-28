from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Track
from .forms import TrackForm


@login_required
def track_list(request):
    """Show all tracks belonging to the logged-in user"""
    tracks = Track.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'tracks/track_list.html', {'tracks': tracks})


@login_required
def track_create(request):
    """Add a new track"""
    if request.method == 'POST':
        form = TrackForm(request.POST)
        if form.is_valid():
            track = form.save(commit=False)
            track.user = request.user
            track.save()
            messages.success(request, 'Track added successfully!')
            return redirect('track_list')
    else:
        form = TrackForm()
    return render(request, 'tracks/track_form.html', {'form': form})


@login_required
def track_update(request, pk):
    """Edit a track"""
    track = get_object_or_404(Track, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TrackForm(request.POST, instance=track)
        if form.is_valid():
            form.save()
            messages.success(request, 'Track updated successfully!')
            return redirect('track_list')
    else:
        form = TrackForm(instance=track)
    return render(request, 'tracks/track_form.html', {'form': form})


@login_required
def track_delete(request, pk):
    """Delete a track"""
    track = get_object_or_404(Track, pk=pk, user=request.user)
    if request.method == 'POST':
        track.delete()
        messages.success(request, 'Track deleted!')
        return redirect('track_list')
    return render(request, 'tracks/track_confirm_delete.html', {'track': track})
