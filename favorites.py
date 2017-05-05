import sublime
import sublime_plugin
import codecs
import os
import shutil
import sys
from os import path
from sublime import Region
import socket
import subprocess
import errno

# version = 1.0.3

if sys.version_info < (3, 3):
    raise RuntimeError('Favorites works with Sublime Text 3 only.')

# ============================================================
# Packages/<package_name>.sublime-package/favorites.py
package_name = path.basename(path.dirname(__file__)).replace('.sublime-package', '')

fav_syntax = 'Packages/'+package_name+'/fav.tmLanguage'
plugin_name = 'favorites'
panel_name = 'Favorites'

def using_Favorite_Files_data():
    return sublime.load_settings(plugin_name+".sublime-settings").get('favorite_files_integration_enabled', True)

# -----------------
def favorites_data_path(per_project):
    file = None

    if per_project:
        project = sublime.active_window().project_file_name()
        if project:
            file = project + '.favorites'
    else:
        file = os.path.join(sublime.packages_path(), 'User', 'favorites.txt')
    
    if file and not path.exists(file):
        with open(file, "w") as f:
            f.write('')

    return file
# -------------------------
def show_integration_constrains_message():
    sublime.error_message('Since you are using "Favorite Files" plugin integration '+
                          'you have to use "Favorite Files" commands via command palette '+
                          'to add, remove or edit the file list.')
    
# -------------------------
def get_favorite_files_data():
    """ 
        Integration with Favorit_Files plugin
        It goes only as far as reading its data file, flattening it and allowing to 
        open files on double-click on the item in the Favorites panel  
    """
    import json

    file_name = os.path.join(sublime.packages_path(), 'User', 'favorite_files_list.json')
    
    with open(file_name) as data_file:    
        data = json.load(data_file)

    result = []    
    for f in data["files"]:
        result.append(f)
         
    for name in data["groups"].keys():
        for f in data["groups"][name]:
            result.append(f)

    return result
# -------------------------
def get_favorites(per_project):
    if using_Favorite_Files_data():
        return get_favorite_files_data()
    else:    
        file = favorites_data_path(per_project)
        lines = []
        if os.path.exists(file):
            with codecs.open(file, "r", encoding='utf8') as f:
                content = f.read().strip()
                if content != '':
                    lines = content.split('\n')

        return [x.strip() for x in lines]
# -------------------------
def set_favorites(lines, per_project):
    if using_Favorite_Files_data():
        show_integration_constrains_message()        
    else:    
        file = favorites_data_path(per_project)
        with codecs.open(file, "w", encoding='utf8') as f:
            f.write('\n'.join(lines))
# -------------------------
def get_favorite_path(index):
    # print(index)    
    lines = get_favorites(False)
    p_lines = get_favorites(True)    

    if index < len(lines):
        return extract_path(lines[index]);

    index -= len(lines)
    index -= items_offset # project favorites will have extra two lines in the header (items_offset)
    if index >= 0 and index < len(p_lines) :    
        # print(index, '/',len(p_lines))
        return extract_path(p_lines[index]);

    return None
# -------------------------
def open_favorite_path(index):
    file = get_favorite_path(index)
    if file:
        focus_prev_view_group()
        open_path(file)
# -------------------------
def add_active_view(arg=None, per_project=False):
    if arg:
        file = arg
    else:
        file = sublime.active_window().active_view().file_name()
    
    lines = get_favorites(per_project)
    if not file in lines:
        lines.append(file)
        set_favorites(lines, per_project)

    refresh_favorites() 
# -------------------------
def focus_prev_view_group():
    try:   
        if favorites_listener.last_active_view:
            if favorites_listener.last_active_view == get_panel_view():
                group, _ = sublime.active_window().get_view_index(favorites_listener.last_active_view)
            else:
                group = 0
            sublime.active_window().focus_group(group)
    except:
        pass
# -------------------------
def remove_from_favorites(arg, per_project):
    file = arg
    lines = []
    for file in get_favorites(per_project):
        if file != arg:
            lines.append(file)
    set_favorites(lines, per_project)
    refresh_favorites() 
# -------------------------
def edit_favorites(per_project):
    if using_Favorite_Files_data():
        show_integration_constrains_message()        
    else:
        focus_prev_view_group()
        open_path(favorites_data_path(per_project))
# -------------------------
def refresh_favorites():
    panel_view = get_panel_view()
    if panel_view:
        panel_view.run_command(plugin_name+'_generator')
# -------------------------
def open_all_favorites(per_project):
    
    for file in get_favorites(per_project):
        view = sublime.active_window().find_open_file(file)
        if not view:
            view = sublime.active_window().open_file(file)

    if view:
        sublime.active_window().focus_view(view)
# -------------------------
def open_path(file):
    view = sublime.active_window().find_open_file(file)
    if not view:
        view = sublime.active_window().open_file(file)
    if view:
        sublime.active_window().focus_view(view)
# -------------------------
def extract_title(text):
    if text:
        parts = text.split('|')
        if len(parts) == 1:
            return path.basename(text.strip())
        else:    
            return parts[0]
    return ''
# -------------------------
def extract_path(text):
    if text:
        parts = text.split('|')
        if len(parts) > 1:
            return parts[len(parts)-1].strip()
        else:    
            return text
# -------------------------
tooltip_template = """
                        <body id=show-scope>
                            <style>
                            body { margin: 0; padding: 20; }
                             p { margin-top: 0;}
                             </style>
                            %s
                        </body>
                    """
# -------------------------
class show_favorites(sublime_plugin.TextCommand):
    def run(self, edit):
        show_panel.run(self, edit);        
# -----------------
items_offset = 2
# -----------------
class favorites_generator(sublime_plugin.TextCommand):
    def run(self, edit):
        panel_view = self.view

        lines = get_favorites(False)

        map = "Add    Edit   Open all"        
        map += "\n-----------------------"        
        for line in lines:
            map += "\n"+extract_title(line)

        project = sublime.active_window().project_file_name()    
        if project:
            map += '\n\n--- "'+path.basename(project).replace('.sublime-project', '" project')+' ---'        
            p_lines = get_favorites(True)
            for line in p_lines:
                map += '\n' + extract_title(line)

        map_syntax = fav_syntax

        panel_view.set_read_only(False)

        all_text = sublime.Region(0, panel_view.size())
        panel_view.replace(edit, all_text, map)
        panel_view.set_scratch(True)

        panel_view.assign_syntax(map_syntax)
        panel_view.set_read_only(True)
# -----------------
class favorites_listener(sublime_plugin.EventListener):
    # -----------------
    last_active_view = None
    # -----------------
    def on_activated(self, view):
        if view != get_panel_view() and view.file_name():
            favorites_listener.last_active_view = view
    # -----------------
    def on_hover(self, view, point, hover_zone):
        if view.file_name() == panel_file():
            row, col = view.rowcol(point)
            if row == 0:
                
                project = sublime.active_window().project_file_name()

                callback = None
                html = ""
                command = view.substr(view.word(point)).lower()
                if command == "add":
                    def add(arg):
                        view.hide_popup()
                        per_project = (arg == 'add_to_proj')
                        add_active_view(None, per_project)
                                            
                    file = sublime.active_window().active_view().file_name()
                    link_open = ''
                    if project:
                        # link_open = file+'<br>'
                        link_open += 'Add active view ('+os.path.basename(file)+')<br>'
                        link_open += '&nbsp;&nbsp;<a href="add">to favorites</a><br>'
                        link_open += '&nbsp;&nbsp;<a href="add_to_proj">to "'+os.path.basename(project).replace('.sublime-project', '')+'" project favorites</a>'
                    else:
                        link_open += '<a href="add">Add active view ('+os.path.basename(file)+') to favorites</a>'


                    html = tooltip_template % (link_open)
                    callback = add
    
                elif command == "edit":
                    def refresh(arg):
                        view.hide_popup()
                        per_project = (arg == 'edit.proj')
                        edit_favorites(per_project)

                    html_content = '<a href="edit">Edit favorites file</a>'
                    if project:
                        html_content += '<br><a href="edit.proj">Edit "'+os.path.basename(project).replace('.sublime-project', '')+'" project favorites file</a>'

                    html = tooltip_template % (html_content)

                    callback = refresh

                elif command == "Open" or "all" :
                    def open(arg):
                        view.hide_popup()
                        per_project = (arg == 'proj')
                        open_all_favorites(per_project)

                    html_content = '<a href="edit">Open all favorites files</a>'
                    if project:
                        html_content += '<br><a href="proj">Open all "'+os.path.basename(project).replace('.sublime-project', '')+'" project favorites files</a>'

                    html = tooltip_template % (html_content)

                    callback = open
    
                elif command == "refresh":
                    def refresh(arg):
                        view.hide_popup()
                        refresh_favorites()
                    html = tooltip_template % ('<a href="edit">Refresh favorites</a>')
                    callback = refresh
    
                else:
                    return

                view.show_popup(html, location=point, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=600, on_navigate=callback)

            else: 
                index = row-items_offset
                global_list = get_favorites(False)
                per_project = (index >= len(global_list))

                file = get_favorite_path(index)

                if file:
                    link_open = file+'<br>'
                    link_open += '&nbsp;&nbsp;<a href="'+file+'">Open in active window</a><br>'
                    link_open += '&nbsp;&nbsp;<a href="remove.'+file+'">Remove from the'
                    if per_project:
                        link_open += " project's favorites</a>"
                    else:    
                        link_open += ' favorites</a>'

                    html = tooltip_template % (link_open)

                    def open(arg):
                        view.hide_popup()
                        if arg.startswith('remove.'):
                            remove_from_favorites(file, per_project)
                        else:
                            open_path(arg)

                    view.show_popup(html, location=point, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=600, on_navigate=open)
    # -----------------
    def on_post_text_command(self, view, command_name, args):
        # process double-click on code panel view`
        if view.file_name() == panel_file():
            if command_name == 'drag_select' and 'by' in args.keys() and args['by'] == 'words':
                point = view.sel()[0].begin()
                row, col = view.rowcol(point)
                view.sel().clear()

                if row > 1:
                    open_favorite_path(row - items_offset)

                elif row == 0:
                    command = view.substr(view.word(point)).lower()
                    if command == 'add':
                        last_view = favorites_listener.last_active_view 
                        if last_view != view:
                            add_active_view(last_view.file_name())

                    elif command == 'edit':
                        edit_favorites()
                    elif command == 'refresh':
                        refresh_favorites()


######################################################################################################################### 
# 
# ============================================================
# Layout management
# ============================================================
def settings():
    return sublime.load_settings(plugin_name+".sublime-settings")
# -----------------    
def panel_file():

    plugin_dir = ''

    if hasattr(sublime, 'cache_path'):
        plugin_dir = sublime.cache_path()
    else:
        plugin_dir = 'cache'
        plugin_dir = os.path.join(os.getcwd(), plugin_dir)

    data_dir = path.join(plugin_dir, panel_name)
    if not path.exists(data_dir):
        os.makedirs(data_dir)
    return path.join(data_dir, panel_name)
# -----------------
def set_layout_columns(count, coll_width=0.75):

    if count == 1:
        sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1]], "cols": [0.0, 1.0], "rows": [0.0, 1.0]})

    elif count == 2:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1]], "cols": [0.0, coll_width, 1.0], "rows": [0.0, 1.0]})

    elif count == 3:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1]], "cols": [0.0, 0.33, 0.66, 1.0], "rows": [0.0, 1.0]})

    elif count == 4:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1], [3, 0, 4, 1]], "cols": [0.0, 0.25, 0.5, 0.75, 1.0], "rows": [0.0, 1.0]})
# -----------------
def centre_line_of(view, region):
    (first_row,c) = view.rowcol(region.begin())
    (last_row,c) = view.rowcol(region.end())
    return int(first_row + (last_row - first_row)/2)
# -----------------
def get_panel_view():
    for v in sublime.active_window().views():
        if v.file_name() == panel_file():
            return v
# -----------------
def refresh_panel_for(view):
    panel_view = get_panel_view()
    if panel_view:
        panel_view.run_command(plugin_name+'_generator')

# ===============================================================================
class event_listener(sublime_plugin.EventListener):
    panel_closed_group = -1
    pre_close_active = None
    can_close = False
    # -----------------
    def on_load(self, view):
        if view.file_name() != panel_file():
            refresh_panel_for(view)
    # -----------------
    def on_pre_close(self, view):
        if view.file_name() == panel_file():
            event_listener.panel_closed_group, x = sublime.active_window().get_view_index(view)
            if len(sublime.active_window().views_in_group(event_listener.panel_closed_group)) == 1:
                event_listener.can_close = True
    # -----------------
    def on_close(self, view):

        def close_panel_group():
            """Removes the panel group, and scales up the rest of the layout"""
            layout = window.get_layout()
            cols = layout['cols']
            cells = layout['cells']
            last_col = len(cols) - 1
            panel_width = cols[len(cols) - 2]

            for i, col in enumerate(cols):
                if col > 0:
                    cols[i] = col/panel_width

            del cols[last_col]
            del cells[len(cells) - 1]
            window.run_command("set_layout", layout)

        def focus_source_code():
            if event_listener.pre_close_active:
                window.focus_group(event_listener.pre_close_active[0])
                window.focus_view(event_listener.pre_close_active[1])

        enabled = settings().get('close_empty_group_on_closing_panel', True)

        if event_listener.can_close and enabled and view.file_name() == panel_file() and event_listener.panel_closed_group != -1:
            window = sublime.active_window()
            event_listener.can_close = False
            close_panel_group()
            sublime.set_timeout(focus_source_code, 100)

        event_listener.panel_closed_group = -1
    # -----------------
    def on_post_save_async(self, view):
        refresh_panel_for(view)
    # -----------------
    def on_activated_async(self, view):
        refresh_panel_for(view)
# ===============================================================================
class scroll_to_left(sublime_plugin.TextCommand):
    # -----------------
    def panel_view(next_focus_view=None):

        def do():
            get_panel_view().run_command('scroll_to_left')

        sublime.set_timeout(do, 100)
    # -----------------
    def run(self, edit):
        region = self.view.visible_region()
        y = self.view.text_to_layout(region.begin())[1]
        self.view.set_viewport_position((0, y), False)

# ===============================================================================
class show_panel:
    # -----------------
    def run(self, edit):

        def create_panel_group():
            """Adds a column on the right, and scales down the rest of the layout"""
            layout = self.view.window().get_layout()
            cols = layout['cols']
            cells = layout['cells']
            last_col = len(cols) - 1
            last_row = len(layout['rows']) - 1
            width = 1 - settings().get("panel_width", 0.17)

            for i, col in enumerate(cols):
                if col > 0:
                    cols[i] = col*width

            cols.append(1)
            newcell = [last_col, 0, last_col + 1, last_row]
            cells.append(newcell)
            window.run_command("set_layout", layout)
            groups = window.num_groups()
            return (groups + 1)

        window = self.view.window()
        groups = window.num_groups()
        current_group = window.active_group()
        current_view = self.view

        panel_view = get_panel_view()

        if not panel_view:
            panel_group = 1

            show_in_new_group = settings().get("show_in_new_group", True)

            if not show_in_new_group:
                if groups == 1:
                    set_layout_columns(2)
                    groups = window.num_groups()

            else:
                panel_group = create_panel_group()

            with open(panel_file(), "w") as file:
                file.write('')

            panel_view = window.open_file(panel_file())
            panel_view.settings().set("word_wrap", False)
            window.set_view_index(panel_view, panel_group, 0)
            panel_view.sel().clear()

            panel_view.settings().set("gutter", False)

            def focus_source_code():
                window.focus_group(current_group)
                window.focus_view(current_view)

            sublime.set_timeout_async(focus_source_code, 100)

        else:
            # close group only if panel is the only file in it
            panel_group = window.get_view_index(panel_view)[0]
            if len(window.views_in_group(panel_group)) == 1:
                event_listener.pre_close_active = [current_group, current_view]
                event_listener.can_close = True
            window.focus_view(panel_view)
            window.run_command("close_file")
# ===============================================================================
