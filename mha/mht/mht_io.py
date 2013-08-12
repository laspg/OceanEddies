import mht
import numpy as np
import scipy.io
from collections import deque
from eddy import Eddy
from node import Node

def load_tracks(src, timesteps):
	"""Load saved data. Returns a dict with all of the saved values (excluding start_date)."""
	mat = scipy.io.loadmat(src, struct_as_record=False)
	tracks = mat['tracks']
	roots = [None]*tracks.shape[0]
	for j in range(tracks.shape[0]):
		track = tracks[j,0]
		parent = None
		for i in range(track.shape[0]):
			pixels = track[i,10:]
			pixels = pixels[pixels > -1]
			eddy = Eddy(track[i,0], track[i,1], track[i,5], pixels, track[i,8],
				track[i,6], track[i,9])
			node = Node(eddy)
			node.final = True
			node.base_depth = int(track[i,2]-1)
			node.score = track[i,3]
			node.missing = bool(track[i,7])
			if parent is None:
				roots[j] = node
			else:
				parent.set_child(node)
			parent = node
	start_depth = mat['end_depth'][0,0]
	prune_depth = mat['prune_depth'][0,0]
	gate_dist = mat['gate_dist'][0,0]
	return {'roots':roots,
		'start_depth':start_depth,
		'prune_depth':prune_depth,
		'gate_dist':gate_dist}

def export_tracks(roots, timesteps, prune_depth):
	all_tracks = deque()
	for root in roots:
		for track in root.tracks():
			end = len(timesteps)-prune_depth-track[0].base_depth
			if end <= 0:
				continue
			sure_track = track[:end]
			all_tracks.append(tuple(sure_track))

	all_tracks = tuple(set(all_tracks))

	eddies_tracks = np.zeros(len(all_tracks), dtype=np.object)
	for i in range(len(all_tracks)):
		eddy_track = []
		max_len = 1
		for j in range(len(all_tracks[i])):
			if type(all_tracks[i][j].obj) is Eddy:
				eddy_track.append(np.array([all_tracks[i][j].obj.Lat,
						all_tracks[i][j].obj.Lon,
						all_tracks[i][0].base_depth+1+j,
						all_tracks[i][j].score,
						all_tracks[i][j].obj.SurfaceArea,
						all_tracks[i][j].obj.Amplitude,
						int(all_tracks[i][j].missing),
						all_tracks[i][j].obj.ThreshFound,
						all_tracks[i][j].obj.MeanGeoSpeed] + all_tracks[i][j].obj.Stats.PixelIdxList.tolist(),
					dtype=np.float64))
				max_len = max(max_len, len(all_tracks[i][j].obj.PixelIdxList) + 10)
		eddies_track_np = np.empty((len(eddy_track),max_len), dtype=np.float64)
		eddies_track_np[:] = -1
		for j in range(len(eddy_track)):
			eddies_track_np[j,:len(eddy_track[j])] = eddy_track[j]
		eddies_tracks[i] = eddies_track_np
	return eddies_tracks

def write_tracks(roots, dest, timesteps, prune_depth, gate_dist = 150):
	"""Write the confirmed portion of the tracks in roots to dest where timesteps is a tuple/list"""
	eddies_tracks = export_tracks(roots, timesteps, prune_depth)
	scipy.io.savemat(dest,
		{'tracks': eddies_tracks,
		 'start_date': np.array(int(timesteps[0]), dtype=np.int),
		 'end_depth': np.array(len(timesteps)-prune_depth, dtype=np.int),
		 'prune_depth': np.array(prune_depth, dtype=np.int),
		 'gate_dist': np.array(gate_dist, dtype=np.float64),
		appendmat=False,
		format='5',
		oned_as='column')

def fmt_print_with_no_root(e_instances, child_score):
	"""Prints out eddies that don't have an instance that starts a new track"""
	for eddy, instances in e_instances.items():
		has_root = False
		for instance in instances:
			if child_score[instance][1] is None:
				has_root = True
		if not has_root:
			print eddy
			for instance in instances:
				print ' ------'
				for child in instance.children:
					print ' ->', child.obj
