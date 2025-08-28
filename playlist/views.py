from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Playlist
from .forms import PlaylistForm


@login_required
def playlist_list(request):
    """List all playlists for the logged-in user"""
    playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'playlist/playlist_list.html', {'playlists': playlists})


@login_required
def playlist_create(request):
    """Create a new playlist"""
    if request.method == 'POST':
        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user
            playlist.save()
            form.save_m2m()  # save track selections
            messages.success(request, "Playlist created successfully!")
            return redirect('playlist_list')
    else:
        form = PlaylistForm()
    return render(request, 'playlist/playlist_form.html', {'form': form})


@login_required
def playlist_update(request, pk):
    """Edit playlist details and tracks"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PlaylistForm(request.POST, instance=playlist)
        if form.is_valid():
            form.save()
            messages.success(request, "Playlist updated successfully!")
            return redirect('playlist_list')
    else:
        form = PlaylistForm(instance=playlist)
    return render(request, 'playlist/playlist_form.html', {'form': form})


@login_required
def playlist_delete(request, pk):
    """Delete a playlist"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    if request.method == 'POST':
        playlist.delete()
        messages.success(request, "Playlist deleted!")
        return redirect('playlist_list')
    return render(request, 'playlist/playlist_confirm_delete.html', {'playlist': playlist})
