'''
Copyright (C) 2014 Jacques Lucke
mail@jlucke.com

Created by Jacques Lucke

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    "name": "Audio to Markers",
    "description": "Work effectively with audio data in the graph editor.",
    "author": "Jacques Lucke",
    "version": (0, 0, 1),
    "blender": (2, 74, 0),
    "location": "View3D",
    "warning": "This is an unstable version",
    "wiki_url": "",
    "category": "Animation" }


import bpy
import os.path
import math
import blf
from bpy.props import *
from bgl import (glBegin, glEnd, glColor4f, GL_POLYGON, glVertex2f, glEnable,
    GL_BLEND, GL_POINTS, glPointSize, GL_LINES, glLineWidth)
from mathutils import Vector    


frequence_ranges = (
    ("0 - 20 Hz", (0, 20)),
    ("20 - 40 Hz", (20, 40)),
    ("40 - 80 Hz", (40, 80)),
    ("80 - 250 Hz", (80, 250)),
    ("250 - 600 Hz", (250, 600)),
    ("600 - 4000 Hz", (600, 4000)),
    ("4 - 6 kHz", (4000, 6000)),
    ("6 - 8 kHz", (6000, 8000)),
    ("8 - 20 kHz", (8000, 20000)) )
frequence_range_dict = {frequence_range[0]: frequence_range[1] for frequence_range in frequence_ranges} 
frequence_range_items = [(frequence_range[0], frequence_range[0], "") for frequence_range in frequence_ranges]

copied_keyframe_locations = []


def apply_frequence_range(self, context):
    settings = context.scene.audio_to_markers
    settings.low_frequence, settings.high_frequence = frequence_range_dict[settings.frequence_range]
        
def frequence_range_changed(self, context):
    update_fcurve_visibility()
        
def update_fcurve_visibility(self = None, context = None):
    fcurves = get_bake_data_fcurves()
    settings = bpy.context.scene.audio_to_markers
    for fcurve in fcurves:
        fcurve.hide = settings.hide_unused_fcurves
        fcurve.lock = settings.lock_sound_fcurves
        fcurve.select = False
    fcurve = get_fcurve_from_current_settings()
    if fcurve:
        fcurve.select = True  
        fcurve.hide = False          


class SoundStripData(bpy.types.PropertyGroup):
    sequence_name = StringProperty(name = "Name", default = "")
    
class BakeData(bpy.types.PropertyGroup):
    intensity = FloatProperty(name = "Intensity", default = 0)
    low = FloatProperty(name = "Low Frequency")
    high = FloatProperty(name = "High Frequency")
    path = StringProperty(name = "File Path", default = "")

class AudioToMarkersSceneSettings(bpy.types.PropertyGroup):
    path = StringProperty(name = "File Path", description = "Path of the music file", default = "")
    sound_strips = CollectionProperty(name = "Music Strips", type = SoundStripData)
    frequence_range = EnumProperty(name = "Frequence Range", items = frequence_range_items, default = "80 - 250 Hz", update = apply_frequence_range)
    low_frequence = FloatProperty(name = "Low Frequence", default = 80, update = frequence_range_changed)
    high_frequence = FloatProperty(name = "High Frequence", default = 250, update = frequence_range_changed)
    bake_data = CollectionProperty(name = "Sound Bake Data", type = BakeData)
    bake_info_text = StringProperty(name = "Info Text", default = "")
    paste_keyframes_info_text = StringProperty(name = "Bake Keyframes Info Text", default = "")
    hide_unused_fcurves = BoolProperty(name = "Hide Unused FCurves", description = "Show only the selected baked data", default = False, update = update_fcurve_visibility)
    lock_sound_fcurves = BoolProperty(name = "Lock Sound Curves", description = "Prevent the user from changing sound fcurves", default = False, update = update_fcurve_visibility)
 
 
 
 
# Sound Bake
############################################### 
 
class AudioManagerPanel(bpy.types.Panel):
    bl_idname = "audio_manager_panel"
    bl_label = "Bake Audio"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.audio_to_markers
        
        col = layout.column(align = False)
        
        row = col.row(align = True)
        row.prop(settings, "path", text = "Sound")
        row.operator("audio_to_markers.select_music_file", icon = "FILE_SOUND", text = "")
        
        if settings.path != "":
            row = col.row(align = True)
            row.operator("audio_to_markers.cache_sounds", icon = "LOAD_FACTORY", text = "")
            row.operator("audio_to_markers.load_into_sequence_editor", text = "Load Sound")
            row.operator("audio_to_markers.remove_sound_strips", icon = "X", text = "")
            
            col = layout.column(align = False)
            
            subcol = col.column(align = True)
            subcol.prop(settings, "frequence_range", text = "")  
            subcol.prop(settings, "low_frequence", text = "Low")
            subcol.prop(settings, "high_frequence", text = "High")
              
            subcol.operator("audio_to_markers.bake_sound", text = "Bake", icon = "RNDCURVE")
            
            row = col.row(align = True)
            if settings.hide_unused_fcurves: row.prop(settings, "hide_unused_fcurves", text = "", icon = "RESTRICT_VIEW_ON")
            else: row.prop(settings, "hide_unused_fcurves", text = "", icon = "RESTRICT_VIEW_OFF")
            
            if settings.lock_sound_fcurves: row.prop(settings, "lock_sound_fcurves", text = "", icon = "LOCKED")
            else: row.prop(settings, "lock_sound_fcurves", text = "", icon = "UNLOCKED")
            
            row.operator("audio_to_markers.bake_all_frequence_ranges")
            row.operator("audio_to_markers.remove_bake_data", icon = "X", text = "")
                
            if settings.bake_info_text != "":
                layout.label(settings.bake_info_text)
            
          
        layout.separator()
          
            
        col = layout.column(align = False)
        selected_fcurves_amount = len(get_active_fcurves())
        row = col.row(align = True)
        row.operator("graph.bake", text = "Bake")
        row.operator("audio_to_markers.unbake_fcurves", text = "Unbake")
        
        subcol = col.column(align = True)
        
        source = CopyBakedFCurveData.get_source_fcurve(return_owner = True)
        if source: copy_text = "Copy from {}.{}[{}]".format(source[0].name, source[1].data_path, source[1].array_index)   
        else: copy_text = "No Copy Source Selected"
        subcol.operator("audio_to_markers.copy_baked_fcurve_data", text = copy_text, icon = "COPYDOWN")   
        
        target_amount = PasteCopiedBakedFCurveData.get_target_amount()
        if len(copied_keyframe_locations) == 0: paste_text = "No Copied Data"
        elif target_amount == 0: paste_text = "No Target Selected"
        elif target_amount == 1: paste_text = "Paste on 1 FCurve"
        else: paste_text = "Paste on {} FCurves".format(target_amount)      
        subcol.operator("audio_to_markers.paste_copied_baked_fcurve_data", text = paste_text, icon = "PASTEDOWN")
        
        if settings.paste_keyframes_info_text != "":
            layout.label(settings.paste_keyframes_info_text)
            
            
        layout.separator()
            
            
        col = layout.column(align = False)
        row = col.row(align = True) 
        row.operator("audio_to_markers.manual_marker_insertion", icon = "MARKER_HLT")    
        row.operator("audio_to_markers.remove_all_markers", icon = "X", text = "")
        
        
        
class SelectMusicFile(bpy.types.Operator):
    bl_idname = "audio_to_markers.select_music_file"
    bl_label = "Select Music File"
    bl_description = "Select a music file with the File Selector"
    bl_options = {"REGISTER", "INTERNAL"}
    
    filepath = StringProperty(subtype = "FILE_PATH")
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        context.scene.audio_to_markers.path = self.filepath
        return {"FINISHED"}
             
             
class LoadIntoSequenceEditor(bpy.types.Operator):
    bl_idname = "audio_to_markers.load_into_sequence_editor"
    bl_label = "Load into Sequence Editor"
    bl_description = "Add a sound strip into the sequence editor at the start frame (hold alt to insert at current frame)"
    bl_options = {"REGISTER", "INTERNAL"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        scene = context.scene
        path = scene.audio_to_markers.path
        name = os.path.basename(path)
        frame = scene.frame_current if event.alt else scene.frame_start
        
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        channel = self.get_empty_channel(scene)
        sequence = context.scene.sequence_editor.sequences.new_sound(name = name, filepath = path, frame_start = frame, channel = channel)
        scene.frame_end = scene.frame_start + sequence.frame_duration
        item = scene.audio_to_markers.sound_strips.add()
        item.sequence_name = sequence.name
        return {"FINISHED"}
    
    def get_empty_channel(self, scene):
        used_channels = [sequence.channel for sequence in scene.sequence_editor.sequences]
        for channel in range(1, 32):
            if not channel in used_channels:
                return channel
        return 0
                  

class CacheSounds(bpy.types.Operator):
    bl_idname = "audio_to_markers.cache_sounds"
    bl_label = "Cache Sounds"
    bl_description = "Load all sounds into RAM"
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        path = context.scene.audio_to_markers.path
        for sound in bpy.data.sounds:
            if sound.filepath ==  path and not sound.use_memory_cache:
                sound.use_memory_cache = True
        return {"FINISHED"}
                     
        
class RemoveSoundStrips(bpy.types.Operator):
    bl_idname = "audio_to_markers.remove_sound_strips"
    bl_label = "Remove Sound Strips"
    bl_description = "Remove all sound strips which were created with this addon"
    bl_options = {"REGISTER", "INTERNAL"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        scene = context.scene
        if not scene.sequence_editor:
            return {"CANCELLED"}
        sequences = scene.sequence_editor.sequences
        sounds = []
        for item in context.scene.audio_to_markers.sound_strips:
            sequence = sequences.get(item.sequence_name)
            if sequence:
                sounds.append(sequence.sound)
                sequences.remove(sequence)
        for sound in sounds:
            sound.use_memory_cache = False
        return {"FINISHED"}
          
          
class BakeAllFrequenceRanges(bpy.types.Operator):
    bl_idname = "audio_to_markers.bake_all_frequence_ranges"
    bl_label = "Bake All Frequences"
    bl_description = "Bake All Frequence Ranges"
    bl_options = {"REGISTER", "INTERNAL"}
    
    @classmethod
    def poll(cls, context):
        return True
        
    def modal(self, context, event):
        if event.type in ["MIDDLEMOUSE", "WHEELDOWNMOUSE", "WHEELUPMOUSE"]: return {"PASS_THROUGH"}
        
        if self.progress_index == len(frequence_ranges) or event.type == "ESC":
            bpy.context.area.tag_redraw()
            self.cancel(context)
            return {"FINISHED"}
        
        self.counter += 1
        if event.type == "TIMER" and self.counter % 30 == 0:
            self.settings.bake_info_text = "Bake: {} of {}".format(self.progress_index+1, len(frequence_ranges))
            context.area.tag_redraw()
            
            if self.progress_index == -1:
                self.progress_index = 0
                return {"RUNNING_MODAL"}
            
            self.settings.low_frequence, self.settings.high_frequence = frequence_ranges[self.progress_index][1]
            bpy.ops.audio_to_markers.bake_sound()
            self.progress_index += 1
        return {"RUNNING_MODAL"}
    
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        self.progress_index = -1
        self.counter = 0
        self.settings = context.scene.audio_to_markers
        self.timer = context.window_manager.event_timer_add(0.001, context.window)
        return {"RUNNING_MODAL"}
    
    def cancel(self, context):
        context.window_manager.event_timer_remove(self.timer)
        self.settings.bake_info_text = ""
        
            
class BakeSound(bpy.types.Operator):
    bl_idname = "audio_to_markers.bake_sound"
    bl_label = "Bake Sound"
    bl_description = "Bake sound on selected fcurves (hold alt to bake from current frame)"
    bl_options = {"REGISTER", "INTERNAL"}
    
    bake_from_start_frame = BoolProperty(default = True)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        self.bake_from_start_frame = not event.alt
        self.execute(context)
        return {"FINISHED"}
    
    def execute(self, context):
        scene = context.scene
        scene.sync_mode = "AUDIO_SYNC"
        
        settings = scene.audio_to_markers
        self.low = settings.low_frequence
        self.high = settings.high_frequence
        self.path = settings.path
        
        frame_before = scene.frame_current
        if self.bake_from_start_frame:
            scene.frame_current = scene.frame_start
          
        fcurve = create_item_and_fcurve_from_current_settings()
        only_select_fcurve(fcurve)
        try:
            fcurve.lock = False
            bpy.ops.graph.sound_bake(
                filepath = self.path,
                low = self.low,
                high = self.high)
        except: 
            print("Could not bake the file")
            return {"CANCELLED"}
        scene.frame_current = frame_before
        return {"FINISHED"}
    
    
class RemoveBakeData(bpy.types.Operator):
    bl_idname = "audio_to_markers.remove_bake_data"
    bl_label = "Remove Bake Data"
    bl_description = "Remove baked sound"
    bl_options = {"REGISTER", "INTERNAL"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        try:    
            fcurves = context.scene.animation_data.action.fcurves
            for fcurve in fcurves:
                if fcurve.data_path.startswith("audio_to_markers.bake_data"):
                    fcurves.remove(fcurve)
        except: pass
        context.scene.audio_to_markers.bake_data.clear()
        update_fcurve_visibility()
        context.area.tag_redraw()
        return {"FINISHED"}
        
        
  

# Create Markers
################################################  

     
class ManualMarkerInsertion(bpy.types.Operator):
    bl_idname = "audio_to_markers.manual_marker_insertion"
    bl_label = "Insert Markers"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return get_active_fcurve()
        
    def invoke(self, context, event):
        self.setup_event_manager()
        
        self.mouse_down_position = get_mouse_position(event)
        self.is_left_mouse_down = False
        self.is_right_mouse_down = False
        self.insertion_preview_data = []
        
        self.selection_type = "NONE"
        self.selection = Rectangle()
        self.selection.top = 10000
        self.selection.bottom = -10000
        self.selection.color = (1.0, 0.1, 0.1, 0.2)
        self.selection.border_color = (0.8, 0.2, 0.1, 0.6)
        self.selection.border_thickness = 2
        
        args = (self, context)
        self._handle = bpy.types.SpaceGraphEditor.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}
    
    def setup_event_manager(self):
        self.manager = EventManager()
        manager = self.manager
        
        e = EventSettings("A", "PRESS", alt = True)
        manager.add_event("PLAY_PAUSE", e)
        
        e = EventSettings("SPACE", "PRESS")
        manager.add_event("PLAY_PAUSE_RESET", e)       
        
        e = EventSettings("ESC", "PRESS")
        manager.add_event("FINISH", e)
        
        e = EventSettings("SPACE", "PRESS", shift = True)
        manager.add_event("FULLSCREEN", e)
        
        e1 = EventSettings("WHEELUPMOUSE", "ANY")
        e2 = EventSettings("WHEELDOWNMOUSE", "ANY")
        e3 = EventSettings("MIDDLEMOUSE", "ANY")
        e4 = EventSettings("MIDDLEMOUSE", "ANY", ctrl = True)
        manager.add_events("PASS_THROUGH", [e1, e2, e3, e4])
    
    def cancel(self, context):
        bpy.types.SpaceGraphEditor.draw_handler_remove(self._handle, "WINDOW")
        
    def modal(self, context, event):
        self.fcurve = get_active_fcurve()
        
        # finish events
        if not self.fcurve:
            self.cancel(context)
            return {"FINISHED"}
        if self.manager.get_name(event) == "FINISH": 
            self.cancel(context)
            return {"FINISHED"}
        
        # pass through events
        if self.manager.get_name(event) == "PASS_THROUGH":
            return {"PASS_THROUGH"}
       
        self.marked_frames = get_marked_frames()
        self.snap_location, snap_frame = self.get_snapping_result(event)
        self.insertion_preview_data = [(self.snap_location, snap_frame not in self.marked_frames)]
        self.selection.right = event.mouse_region_x 
        
        self.update_mouse_press_status(event)
               
        self.play_or_pause_animation_handler(event)  
        self.insert_marker_handler(event, snap_frame)
        self.remove_markers_handler(event)
        self.insert_multiple_markers_handler(event)
        
        if self.manager.get_name(event) == "FULLSCREEN" and self.is_mouse_inside(event, context.area):
            bpy.ops.screen.screen_full_area()
            return {"RUNNING_MODAL"}
        
        context.area.tag_redraw()    
        
        if self.is_mouse_inside(event, context.region) or self.is_left_mouse_down or self.is_right_mouse_down:
            return {"RUNNING_MODAL"}
        else:
            return {"PASS_THROUGH"}
        
    def update_mouse_press_status(self, event):
        if event.type == "LEFTMOUSE":
            if event.value == "PRESS" and self.is_mouse_inside(event, bpy.context.region):
                self.mouse_down_position = get_mouse_position(event)
                self.is_left_mouse_down = True
            if event.value == "RELEASE":
                self.is_left_mouse_down = False
                
        if event.type == "RIGHTMOUSE":
            if event.value == "PRESS" and self.is_mouse_inside(event, bpy.context.region):
                self.mouse_down_position = get_mouse_position(event)
                self.is_right_mouse_down = True
            if event.value == "RELEASE":
                self.is_right_mouse_down = False  
            
    def play_or_pause_animation_handler(self, event):
        if self.manager.get_name(event) == "PLAY_PAUSE":
            bpy.ops.screen.animation_play()
        if self.manager.get_name(event) == "PLAY_PAUSE_RESET":
            if not bpy.context.screen.is_animation_playing:
                frame = bpy.context.region.view2d.region_to_view(event.mouse_region_x, 0)[0]
                bpy.context.scene.frame_current = frame
            bpy.ops.screen.animation_play()
            
    def is_mouse_over_side_bars(self, event):
        return self.is_mouse_inside(event, bpy.context.area) and \
            not self.is_mouse_inside(event, bpy.context.region)
            
    def insert_marker_handler(self, event, snap_frame):
        if self.selection_type != "NONE" or event.alt or event.ctrl: return
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if self.is_mouse_inside(event, bpy.context.region):
                insert_markers([snap_frame])
                
    def remove_markers_handler(self, event): 
        if self.selection_type == "INSERT": return
        if self.is_right_mouse_down and (get_mouse_position(event)-self.mouse_down_position).length > 14:
            self.selection_type = "REMOVE"
            self.selection.left = self.mouse_down_position.x
            self.selection.right = event.mouse_region_x
        if self.selection_type == "REMOVE" and not self.is_right_mouse_down:
            self.selection_type = "NONE"
            start_frame = self.get_frame_under_region_x(self.selection.left)
            end_frame = self.get_frame_under_region_x(self.selection.right)
            remove_markers(start_frame, end_frame)
                
    def insert_multiple_markers_handler(self, event):
        if self.selection_type == "REMOVE" or event.alt or event.ctrl or event.shift: return
        if self.is_left_mouse_down and (get_mouse_position(event)-self.mouse_down_position).length > 14:
            self.selection_type = "INSERT"
            self.selection.left = self.mouse_down_position.x
            self.selection.right = event.mouse_region_x
        if self.selection_type == "INSERT":
            threshold = self.get_view_y_under_region_y(event.mouse_region_y)
            bpy.context.space_data.cursor_position_y = threshold
            insertion_frames = self.get_insertion_frames(event)
            locations = self.get_region_points_from_frames(insertion_frames)
            self.insertion_preview_data = []
            for frame, location in zip(insertion_frames, locations):
                self.insertion_preview_data.append((location, frame not in self.marked_frames))
            
        if self.selection_type == "INSERT" and not self.is_left_mouse_down:
            self.selection_type = "NONE"
            frames = self.get_insertion_frames(event)
            insert_markers(frames)
            
    def get_insertion_frames(self, event):
        start_frame = self.get_frame_under_region_x(self.selection.left)
        end_frame = self.get_frame_under_region_x(self.selection.right)
        threshold = bpy.context.space_data.cursor_position_y 
        return get_high_frames(self.fcurve, start_frame, end_frame, threshold)
    
    def get_region_points_from_frames(self, frames):
        points = []
        view = bpy.context.region.view2d
        for frame in frames:
            value = self.fcurve.evaluate(frame)
            points.append(view.view_to_region(frame, value))
        return points
    
    def get_snapping_result(self, event):
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y
        
        view = bpy.context.region.view2d
        if event.shift:
            snap_frame = round(self.get_frame_under_region_x(mouse_x))
        else:
            start_frame = round(self.get_frame_under_region_x(mouse_x-20))
            end_frame = round(self.get_frame_under_region_x(mouse_x+20))
            
            snap_frame = 0
            max_value = -1000000
            for frame in range(start_frame, end_frame):
                value = self.fcurve.evaluate(frame)
                if value > max_value:
                    snap_frame = frame
                    max_value = value
        
        snap_value = self.fcurve.evaluate(snap_frame)        
        snap_location = view.view_to_region(snap_frame, snap_value)
        return snap_location, snap_frame
    
    def get_frame_under_region_x(self, x):
        return bpy.context.region.view2d.region_to_view(x, 0)[0]
    
    def get_view_y_under_region_y(self, y):
        return bpy.context.region.view2d.region_to_view(0, y)[1]
    
    def replay_sound(self, event, seconds):
        scene = bpy.context.scene
        scene.frame_current -= scene.render.fps * seconds
    
    def is_mouse_inside(self, event, area):
        padding = 5
        return padding <= event.mouse_region_x < area.width-padding and padding < event.mouse_region_y < area.height-padding
        
    def draw_callback_px(tmp, self, context):
        if self.selection_type != "NONE":
            if self.selection_type == "REMOVE":
                self.selection.color = (1.0, 0.1, 0.1, 0.07)
                self.selection.border_color = (0.8, 0.2, 0.1, 0.4) 
            elif self.selection_type == "INSERT":
                self.selection.color = (0.1, 1.0, 0.1, 0.07)
                self.selection.border_color = (0.2, 0.8, 0.1, 0.4) 
            self.selection.draw()
        
        if self.selection_type != "REMOVE":    
            for location, enabled in self.insertion_preview_data:
                self.draw_marker(location, enabled)
        self.draw_operator_help()
        
    def draw_marker(self, position, enabled = True):
        if enabled: 
            color = (0.4, 0.8, 0.2, 0.7)
            size = 8.0
        else: 
            color = (0.8, 0.8, 0.8, 0.5)
            size = 5.0
        draw_dot(position, size, color)
        
    def draw_operator_help(self): 
        font_id = 0
        marker_amount = self.get_marker_amount_before_current_frame()
        text = [
            "LMB (drag): Insert Markers",
            "RMB drag: Remove Markers",
            "Space: Play from cursor/Pause",
            "CTRL: Set frame to cursor",
            "ESC: Finish operator" ]
        
        background = Rectangle()
        background.color = (0.0, 0.0, 0.0, 0.6)
        background.border_color = (0.0, 0.0, 0.0, 0.9)
        background.top = bpy.context.area.height
        background.bottom = background.top - 90 - len(text)*30
        background.left = 0
        background.right = 220
        
        background.draw()
        
        glColor4f(0.9, 0.9, 0.9, 1.0)
        blf.size(font_id, 12, 80)
        top = bpy.context.area.height - 60
        for i, line in enumerate(text):
            blf.position(font_id, 20, top - i * 30, 0)
            blf.draw(font_id, line)
            
        blf.position(font_id, 20, top - len(text) * 30 - 7, 0)
        blf.size(font_id, 13, 80)
        blf.draw(font_id, "Counter: {}".format(marker_amount))
         
    def get_marker_amount_before_current_frame(self):
        amount = 0
        scene = bpy.context.scene
        for marker in scene.timeline_markers:
            if marker.frame <= scene.frame_current:
                amount += 1
        return amount  
            
class RemoveAllMarkers(bpy.types.Operator):
    bl_idname = "audio_to_markers.remove_all_markers"
    bl_label = "Remove all Markers"
    bl_description = "Remove all markers in this scene"
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        for marker in context.scene.timeline_markers:
            context.scene.timeline_markers.remove(marker)
        return {"FINISHED"}
                

def draw_dot(position, size, color):
    glColor4f(*color)
    glEnable(GL_BLEND)
    glPointSize(size)
    glBegin(GL_POINTS)
    glVertex2f(*position)
    glEnd()     
    

        
def insert_markers(frames):
    scene = bpy.context.scene
    marked_frames = get_marked_frames()
    for frame in frames:
        if frame not in marked_frames:
            scene.timeline_markers.new(name = "#{}".format(frame), frame = frame)  
            
def get_marked_frames():
    return [marker.frame for marker in bpy.context.scene.timeline_markers]          
            
def remove_markers(start_frame, end_frame):
    start_frame, end_frame = sorted([start_frame, end_frame])
    scene = bpy.context.scene
    for marker in scene.timeline_markers:
        if start_frame <= marker.frame <= end_frame:
            scene.timeline_markers.remove(marker)   
            
def get_high_frames(sound_curve, start, end, threshold):
    start, end = sorted([start, end])
    frames = []
    is_over_threshold = False
    for frame in range(round(start), round(end)):
        value = highest_value_of_frame(sound_curve, frame)
        next_value = highest_value_of_frame(sound_curve, frame + 1)
        if value > next_value > threshold and not is_over_threshold:
            is_over_threshold = True
            frames.append(frame)
        if value < threshold:
            is_over_threshold = False
    return frames     

def highest_value_of_frame(fcurve, frame):
    return max(fcurve.evaluate(frame-0.5), fcurve.evaluate(frame-0.25), fcurve.evaluate(frame), fcurve.evaluate(frame+0.25))
                                
                        




# Baked FCurves
################################################                        

                       
class UnbakeFCurve(bpy.types.Operator):
    bl_idname = "audio_to_markers.unbake_fcurves"
    bl_label = "Unbake FCurves"
    bl_description = "Convert selected fcurves to keyframes."
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return len(list(cls.fcurves_with_owners_to_unbake())) > 0
    
    def execute(self, context):
        for object, fcurve in self.fcurves_with_owners_to_unbake():
            if len(fcurve.sampled_points) > 0 and not fcurve.lock:
                self.unbake_fcurve(object, fcurve)
        return {"FINISHED"}
    
    @classmethod
    def fcurves_with_owners_to_unbake(cls):
        for fcurve_with_owner in get_active_fcurves(return_owner = True):
            fcurve = fcurve_with_owner[1]
            if len(fcurve.sampled_points) > 0 and not fcurve.lock:
                yield fcurve_with_owner
    
    def unbake_fcurve(self, object, fcurve):
        sample_locations = [(sample.co[0], sample.co[1]) for sample in fcurve.sampled_points]
        keyframe_locations = []
        for i, co in enumerate(sample_locations):
            if i == 0: continue
            if co[1] != sample_locations[i-1][1]:
                keyframe_locations.append(co)
        data_path = fcurve.data_path
        index = fcurve.array_index
        object.animation_data.action.fcurves.remove(fcurve)
        fcurve = object.animation_data.action.fcurves.new(data_path = data_path, index = index)
        for co in keyframe_locations:
            keyframe = fcurve.keyframe_points.insert(frame = co[0], value = co[1])
            keyframe.interpolation = "LINEAR"
        bpy.context.area.tag_redraw()  
        
        
class CopyBakedFCurveData(bpy.types.Operator):
    bl_idname = "audio_to_markers.copy_baked_fcurve_data"
    bl_label = "Copy Baked Data"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return cls.get_source_fcurve()
    
    def execute(self, context):
        global copied_keyframe_locations
        copied_keyframe_locations = []
        baked_fcurve = self.get_source_fcurve()
        if baked_fcurve:
            for sample in baked_fcurve.sampled_points:
                copied_keyframe_locations.append((sample.co[0], sample.co[1]))
        return {"FINISHED"}
    
    @classmethod
    def get_source_fcurve(cls, return_owner = False):
        for fcurve_with_owner in get_active_fcurves(return_owner = True):
            if len(fcurve_with_owner[1].sampled_points) > 0:
                if return_owner: return fcurve_with_owner
                else: return fcurve_with_owner[1]
        return None
    
    
class PasteCopiedBakedFCurveData(bpy.types.Operator):
    bl_idname = "audio_to_markers.paste_copied_baked_fcurve_data"
    bl_label = "Paste Copied Bake Data"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return cls.get_target_amount() > 0 and len(copied_keyframe_locations) > 0
        
    def modal(self, context, event):
        if event.type == "ESC": 
            self.cancel(context)
            return {"CANCELLED"}
        if event.type in ["MIDDLEMOUSE", "WHEELDOWNMOUSE", "WHEELUPMOUSE"]: return {"PASS_THROUGH"}
        if event.type == "TIMER" and self.counter % 3 == 0:
            for fcurve in self.fcurves:
                for i in range(self.progress_index, self.progress_index + self.chunk_size):
                    if i >= self.keyframe_amount: 
                        self.cancel(context)
                        return {"FINISHED"}
                    co = copied_keyframe_locations[i]
                    keyframe = fcurve.keyframe_points.insert(frame = co[0], value = co[1])
                    keyframe.interpolation = "LINEAR"
            self.progress_index += self.chunk_size
            self.settings.paste_keyframes_info_text = "{} of {} Keyframes".format(self.progress_index, self.keyframe_amount)
            context.area.tag_redraw()
            
        self.counter += 1
            
        return {"RUNNING_MODAL"}
    
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        self.progress_index = 0
        self.counter = 0
        self.chunk_size = 30
        self.fcurves = list(self.selected_unbaked_fcurves())
        self.keyframe_amount = len(copied_keyframe_locations)
        self.settings = context.scene.audio_to_markers
        self.settings.paste_keyframes_info_text = "{} of {} Keyframes".format(0, self.keyframe_amount)
        self.timer = context.window_manager.event_timer_add(0.005, context.window)
        return {"RUNNING_MODAL"}
    
    def cancel(self, context):
        context.window_manager.event_timer_remove(self.timer)
        self.settings.paste_keyframes_info_text = ""
        
    @classmethod
    def get_target_amount(cls):
        return len(list(cls.selected_unbaked_fcurves()))
    
    @classmethod
    def selected_unbaked_fcurves(cls):
        for fcurve in get_active_fcurves():
            if len(fcurve.sampled_points) == 0: yield fcurve
            
                              
 

# Helper
################################################ 

def get_active_fcurve():
    fcurves = get_active_fcurves()
    if len(fcurves) > 0: return fcurves[0]
    return None

def get_active_fcurves(return_owner = False):
    fcurves_with_owner = []
    for object in bpy.context.selected_objects + [bpy.context.scene]:
        try:
            for fcurve in object.animation_data.action.fcurves:
                if fcurve.select: fcurves_with_owner.append((object, fcurve))
        except: pass
    if return_owner: return fcurves_with_owner
    return [fcurve_with_owner[1] for fcurve_with_owner in fcurves_with_owner]                                           

def create_item_and_fcurve_from_current_settings():
    item = get_current_bake_item()
    if not item:
        item = new_bake_item_from_settings()
    fcurve = get_fcurve_from_current_settings()
    if not fcurve:
        item.keyframe_insert("intensity", frame = 0)
        fcurve = get_fcurve_from_current_settings()
    return fcurve
        
def new_bake_item_from_settings():
    settings = bpy.context.scene.audio_to_markers  
    item = bpy.context.scene.audio_to_markers.bake_data.add()
    item.path = settings.path
    item.low = settings.low_frequence
    item.high = settings.high_frequence      
    return item           
                
def get_fcurve_from_current_settings():
    index = get_current_bake_item(return_type = "INDEX")
    return get_fcurve_from_bake_data_index(index)

def get_current_bake_item(return_type = "ITEM"):
    current_item = None
    index = -1
    settings = bpy.context.scene.audio_to_markers  
    for i, item in enumerate(settings.bake_data):
        if is_item_equal_to_settings(item, settings):
            current_item = item
            index = i
    if return_type == "ITEM": return current_item
    else: return index
        
def is_item_equal_to_settings(item, settings):
    return item.path == settings.path and \
            item.low == settings.low_frequence and \
            item.high == settings.high_frequence            
  
def get_bake_data_fcurves():
    fcurves = []
    for i in range(len(bpy.context.scene.audio_to_markers.bake_data)):
        fcurve = get_fcurve_from_bake_data_index(i)
        if fcurve: fcurves.append(fcurve)
    return fcurves
  
def get_fcurve_from_bake_data_index(index):
    return get_fcurve_from_path(bpy.context.scene, "audio_to_markers.bake_data[{}].intensity".format(index))
  
def get_fcurve_from_path(object, data_path):
    try:
        for fcurve in object.animation_data.action.fcurves:
            if fcurve.data_path == data_path:
                return fcurve
    except: pass
    return None                         
                         
def only_select_fcurve(fcurve):
    deselect_all_fcurves()
    fcurve.select = True
    
def deselect_all_fcurves():
    for fcurve in iter_all_fcurves():
        fcurve.select = False
 
def iter_all_fcurves():
    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            yield fcurve
        
def get_mouse_position(event):
    return Vector((event.mouse_region_x, event.mouse_region_y))        
 
class Line:
    def __init__(self):
        self.start = Vector((0, 0))
        self.end = Vector((0, 0))
        
    def set_start(self, event):
        self.start = Vector((event.mouse_region_x, event.mouse_region_y))
    def set_end(self, event):
        self.end = Vector((event.mouse_region_x, event.mouse_region_y))
        
    def draw(self, thickness = 2, color = (0.2, 0.2, 0.2, 1.0)):
        glLineWidth(thickness)
        glColor4f(*color)
        glBegin(GL_LINES)
        glVertex2f(*self.start)
        glVertex2f(*self.end)
        glEnd()   
        glLineWidth(1)   
        
class Rectangle:
    def __init__(self):
        self.top = 1000
        self.bottom = 0
        self.left = 0
        self.right = 1000
        self.color = (0.2, 0.2, 0.2, 1.0)
        self.border_color = (0.0, 0.0, 0.0, 1.0)
        self.border_thickness = 0
        
    def draw(self):
        top_left = (self.left, self.top)
        top_right = (self.right, self.top)
        bottom_left = (self.left, self.bottom)
        bottom_right = (self.right, self.bottom)
        
        glEnable(GL_BLEND)
        glColor4f(*self.color)
        glBegin(GL_POLYGON)
        for x, y in [top_left, top_right, bottom_right, bottom_left]:
            glVertex2f(x, y)
        glEnd() 
        
        lines = [
            (top_left, top_right), 
            (top_right, bottom_right), 
            (bottom_right, bottom_left), 
            (bottom_left, top_left) ]
        glBegin(GL_LINES)
        for start, end in lines:
            draw_line(start, end, self.border_thickness, self.border_color)
        glEnd()
        
        
def draw_line(start, end, thickness, color):
    glLineWidth(thickness)
    glColor4f(*color)
    glBegin(GL_LINES)
    glVertex2f(*start)
    glVertex2f(*end)
    glEnd()   
    glLineWidth(1)    
    
    
from collections import defaultdict    
class EventManager:
    def __init__(self):
        self.events = defaultdict(list)
        
    def add_event(self, name, event_settings):
        self.events[name].append(event_settings)
        
    def add_events(self, name, event_settings):
        self.events[name].extend(event_settings)
        
    # assumes that only one event can happen at the same time    
    def get_name(self, event):
        names = self.get_names(event)
        if len(names) > 0:
            return names[0]
        return None

    def get_names(self, event):
        names = []
        for name, event_settings in self.events.items():
            for event_setting in event_settings:
                if event_setting.fits_event(event):
                    names.append(name)
                    break
        return names

class EventSettings:
    def __init__(self, event_type, event_value, shift = False, ctrl = False, alt = False):
        self.type = event_type
        self.value = event_value
        self.shift = shift
        self.ctrl = ctrl
        self.alt = alt

    def fits_event(self, event):
        return event.type == self.type and \
                (event.value == self.value or self.value == "ANY") and \
                event.shift == self.shift and \
                event.ctrl == self.ctrl and \
                event.alt == self.alt 
        
        
        
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.audio_to_markers = PointerProperty(name = "Audio to Markers", type = AudioToMarkersSceneSettings)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()
            
  
# def update(scene):
    # pass              
            
# bpy.app.handlers.scene_update_post.clear()      
# bpy.app.handlers.scene_update_post.append(update)       
        