import pygame
import random
import sys
import textwrap

pygame.init()

# Utility Functions
def render_text_list(surface, text_lines, font, rect, color=(0, 0, 0)):
    """
    Renders a list of text lines within a given rectangle, handling text wrapping.
    """
    y_offset = rect.y
    for line in text_lines:
        wrapped_lines = textwrap.wrap(line, width=40)  # Adjust width as needed
        for wrapped_line in wrapped_lines:
            text_surf = font.render(wrapped_line, True, color)
            surface.blit(text_surf, (rect.x, y_offset))
            y_offset += text_surf.get_height() + 5  # 5 pixels between lines

class Application:
    """
    The main application class responsible for initializing and running the main loop.
    It delegates specific responsibilities to other classes to maintain single responsibility.
    """
    def __init__(self):
        pygame.init()
        # Set up initial screen dimensions
        self.screen_width, self.screen_height = 800, 600
        self.TASKBAR_HEIGHT = 40
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Pygame Window Manager")
        self.is_fullscreen = False

        # Create taskbar
        self.taskbar = Taskbar(self)

        # Window manager
        self.window_manager = WindowManager(self)

        # Keyboard shortcuts
        self.KEYBOARD_SHORTCUTS = {
            ('n',): 'new_window',
            ('w',): 'close_window',
            ('f',): 'toggle_fullscreen',
        }

        # Other variables
        self.running = True
        self.selected_window = None
        self.menu_stack = []

        # Store previous screen size for scaling calculations
        self.prev_screen_width = self.screen_width
        self.prev_screen_height = self.screen_height

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            # Update and draw everything
            self.update()
            self.draw()

        # Quit pygame
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        """
        Handles all incoming events, delegating to appropriate managers or handling globally.
        """
        if event.type == pygame.QUIT:
            self.running = False

        # Handle keyboard shortcuts
        elif event.type == pygame.KEYDOWN:
            modifiers = pygame.key.get_mods()
            if modifiers & pygame.KMOD_CTRL:
                if event.key == pygame.K_n:
                    # Ctrl+N: New Window
                    new_x = random.randint(50, self.screen_width - 350)
                    new_y = random.randint(50, self.screen_height - self.TASKBAR_HEIGHT - 250)
                    new_window = DraggableWindow(new_x, new_y, 300, 200, self, title=f"Window {len(self.window_manager.windows)+1}")
                    self.window_manager.add_window(new_window)
                elif event.key == pygame.K_w:
                    # Ctrl+W: Close Selected Window
                    if self.selected_window:
                        self.selected_window.minimize()
                        self.selected_window = None
                elif event.key == pygame.K_f:
                    # Ctrl+F: Toggle Fullscreen
                    if self.is_fullscreen:
                        self.screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
                        self.is_fullscreen = False
                    else:
                        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        self.is_fullscreen = True
                    # Update screen dimensions
                    self.screen_width, self.screen_height = self.screen.get_size()
                    # Update taskbar rect
                    self.taskbar.rect.topleft = (0, self.screen_height - self.TASKBAR_HEIGHT)
                    self.taskbar.rect.size = (self.screen_width, self.TASKBAR_HEIGHT)

        # Handle window resize
        elif event.type == pygame.VIDEORESIZE:
            old_width, old_height = self.screen_width, self.screen_height  # Store old dimensions
            self.screen_width, self.screen_height = event.w, event.h
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
            # Update taskbar rect
            self.taskbar.rect.topleft = (0, self.screen_height - self.TASKBAR_HEIGHT)
            self.taskbar.rect.size = (self.screen_width, self.TASKBAR_HEIGHT)

            # Calculate scaling factors
            scale_x = self.screen_width / self.prev_screen_width
            scale_y = self.screen_height / self.prev_screen_height

            # Update all windows
            for window in self.window_manager.windows:
                # Scale position
                new_x = int(window.rect.x * scale_x)
                new_y = int(window.rect.y * scale_y)

                # Scale size
                new_width = int(window.rect.width * scale_x)
                new_height = int(window.rect.height * scale_y)

                window.rect.x = new_x
                window.rect.y = new_y
                window.rect.width = max(new_width, 150)  # Ensure minimum width
                window.rect.height = max(new_height, 100)  # Ensure minimum height

                # Ensure window is within the new screen boundaries
                self.constrain_window_within_screen(window)

            # Update previous screen size
            self.prev_screen_width = self.screen_width
            self.prev_screen_height = self.screen_height

        # Handle mouse events
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.taskbar.rect.collidepoint(event.pos):
                    self.taskbar.handle_event(event)
                    return  # Skip further processing

                if self.menu_stack:
                    current_menu = self.menu_stack[-1]
                    if current_menu.rect.collidepoint(event.pos):
                        new_popup = current_menu.handle_event(event)
                        if new_popup:
                            self.menu_stack.append(new_popup)
                    else:
                        # Clicked outside the current menu: close all menus
                        self.menu_stack.clear()
                else:
                    # No menus open, handle window interactions
                    self.window_manager.handle_event(event)
            elif event.button == 3:  # Right mouse button
                if self.menu_stack:
                    current_menu = self.menu_stack[-1]
                    if current_menu.rect.collidepoint(event.pos):
                        # Right-click inside the current menu: return to previous menu
                        self.menu_stack.pop()
                    else:
                        # Clicked outside the current menu: close all menus
                        self.menu_stack.clear()
                else:
                    # Open main menu for the window under the cursor
                    for window in reversed(self.window_manager.windows):
                        if window.rect.collidepoint(event.pos):
                            main_menu = MainMenuWindow(event.pos[0], event.pos[1], window, self)
                            self.menu_stack.append(main_menu)
                            break
        else:
            if self.menu_stack:
                current_menu = self.menu_stack[-1]
                new_popup = current_menu.handle_event(event)
                if new_popup:
                    self.menu_stack.append(new_popup)
            self.window_manager.handle_event(event)

    def constrain_window_within_screen(self, window):
        """
        Adjust the window's position and size to ensure it remains within the main screen boundaries.
        """
        # Ensure the window's x position is within the screen
        if window.rect.x + window.rect.width > self.screen_width:
            window.rect.x = max(self.screen_width - window.rect.width, 0)
        
        # Ensure the window's y position is within the screen (excluding taskbar)
        if window.rect.y + window.rect.height > self.screen_height - self.TASKBAR_HEIGHT:
            window.rect.y = max(self.screen_height - self.TASKBAR_HEIGHT - window.rect.height, 0)
        
        # Optionally, adjust width and height if they exceed the screen
        if window.rect.width > self.screen_width:
            window.rect.width = self.screen_width
        if window.rect.height > self.screen_height - self.TASKBAR_HEIGHT:
            window.rect.height = self.screen_height - self.TASKBAR_HEIGHT

    def update(self):
        """
        Update logic if necessary. Currently unused but can be expanded.
        """
        pass

    def draw(self):
        """
        Draws all components onto the screen.
        """
        self.screen.fill((30, 30, 30))
        self.window_manager.draw(self.screen)
        for menu in self.menu_stack:
            menu.draw(self.screen)
        self.taskbar.draw(self.screen)
        pygame.display.flip()

class WindowManager:
    """
    Manages all window instances, handling their addition, removal, event delegation, and drawing.
    """
    def __init__(self, application):
        self.application = application
        self.windows = []

    def add_window(self, window):
        self.windows.append(window)

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)

    def bring_to_front(self, window):
        """
        Moves the specified window to the end of the list to render it on top.
        """
        if window in self.windows:
            self.windows.append(self.windows.pop(self.windows.index(window)))

    def handle_event(self, event):
        """
        Delegates event handling to windows, starting from the topmost window.
        """
        for window in reversed(self.windows):
            result = window.handle_event(event)
            if window.selected:
                self.bring_to_front(window)
                self.application.selected_window = window
                break

    def draw(self, surface):
        for window in self.windows:
            window.draw(surface)

class Taskbar:
    """
    Represents the taskbar, managing minimized windows and providing buttons to restore them.
    """
    def __init__(self, application):
        self.application = application
        self.minimized_windows = []
        self.rect = pygame.Rect(0, application.screen_height - application.TASKBAR_HEIGHT, application.screen_width, application.TASKBAR_HEIGHT)
        self.color = (50, 50, 50)
        
    def add_window(self, window):
        if window not in self.minimized_windows:
            self.minimized_windows.append(window)

    def remove_window(self, window):
        if window in self.minimized_windows:
            self.minimized_windows.remove(window)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        # Draw minimized window buttons
        for idx, window in enumerate(self.minimized_windows):
            button_width = 100
            button_height = self.application.TASKBAR_HEIGHT - 10
            spacing = 10
            x = spacing + idx * (button_width + spacing)
            y = self.application.screen_height - self.application.TASKBAR_HEIGHT + 5
            button_rect = pygame.Rect(x, y, button_width, button_height)
            pygame.draw.rect(surface, (100, 100, 100), button_rect)
            pygame.draw.rect(surface, (255, 255, 255), button_rect, 2)

            # Render window title
            font = pygame.font.Font(None, 24)
            title_surf = font.render(window.title, True, (255, 255, 255))
            surface.blit(title_surf, (x + 5, y + 10))

    def handle_event(self, event):
        """
        Handles clicks on taskbar buttons to restore minimized windows.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, window in enumerate(self.minimized_windows):
                button_width = 100
                button_height = self.application.TASKBAR_HEIGHT - 10
                spacing = 10
                x = spacing + idx * (button_width + spacing)
                y = self.application.screen_height - self.application.TASKBAR_HEIGHT + 5
                button_rect = pygame.Rect(x, y, button_width, button_height)
                if button_rect.collidepoint(event.pos):
                    window.restore()
                    self.remove_window(window)
                    self.application.window_manager.bring_to_front(window)
                    break

class Window:
    """
    Base class for all window types, providing common attributes and methods.
    """
    def __init__(self, x, y, width, height, title="Window"):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.minimized = False
        self.maximized = False
        self.selected = False

    def draw(self, surface):
        pass  # To be implemented in subclasses

    def handle_event(self, event):
        pass  # To be implemented in subclasses

class DraggableWindow(Window):
    """
    A window that can be dragged, resized, minimized, and maximized.
    """
    def __init__(self, x, y, width, height, application, color=(100, 100, 250), title="Window"):
        super().__init__(x, y, width, height, title)
        self.application = application  # Reference to the application
        self.color = color
        # Initialize other attributes
        self.selected = False
        self.resize = False
        self.offset_x = 0
        self.offset_y = 0
        self.prev_rect = self.rect.copy()  # Stores previous size and position for restoring
        self.dynamic_options = []  # List of dynamic menu options

        # Buttons dimensions
        self.button_width = 20
        self.button_height = 20
        self.minimize_button = pygame.Rect(0, 0, self.button_width, self.button_height)
        self.maximize_button = pygame.Rect(0, 0, self.button_width, self.button_height)

    def draw(self, surface):
        if self.minimized:
            return  # Do not draw minimized windows

        # Draw drop shadow
        shadow_color = (0, 0, 0, 100)  # Semi-transparent black
        shadow_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, shadow_color, shadow_surface.get_rect(), border_radius=5)
        surface.blit(shadow_surface, (self.rect.x + 5, self.rect.y + 5))

        # Draw window body
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2, border_radius=5)

        # Draw title bar
        title_bar_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(surface, (70, 130, 180), title_bar_rect, border_radius=5)

        # Draw title text
        font = pygame.font.Font(None, 24)
        title_surf = font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surf, (self.rect.x + 10, self.rect.y + 5))

        # Update button positions
        self.minimize_button.topleft = (self.rect.right - 2 * (self.button_width + 5), self.rect.y + 5)
        self.maximize_button.topleft = (self.rect.right - (self.button_width + 5), self.rect.y + 5)

        # Draw minimize button
        pygame.draw.rect(surface, (200, 200, 0), self.minimize_button)
        pygame.draw.line(surface, (0, 0, 0), self.minimize_button.topleft, self.minimize_button.topright, 2)

        # Draw maximize button
        pygame.draw.rect(surface, (0, 200, 0), self.maximize_button)
        pygame.draw.rect(surface, (0, 0, 0), self.maximize_button, 2)

        # Draw resize handle
        resize_handle = pygame.Rect(self.rect.right - 10, self.rect.bottom - 10, 10, 10)
        pygame.draw.rect(surface, (250, 100, 100), resize_handle)

    def handle_event(self, event):
        if self.minimized:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Check if minimize button clicked
                if self.minimize_button.collidepoint(event.pos):
                    self.minimize()
                    return 'minimized'

                # Check if maximize button clicked
                if self.maximize_button.collidepoint(event.pos):
                    self.toggle_maximize()
                    return 'maximized'

                # Check if resize handle clicked
                resize_handle = pygame.Rect(self.rect.right - 10, self.rect.bottom - 10, 10, 10)
                if resize_handle.collidepoint(event.pos):
                    self.selected = True
                    self.resize = True
                    self.offset_x = event.pos[0] - self.rect.right
                    self.offset_y = event.pos[1] - self.rect.bottom
                elif self.rect.collidepoint(event.pos):
                    self.selected = True
                    self.resize = False
                    self.offset_x = event.pos[0] - self.rect.x
                    self.offset_y = event.pos[1] - self.rect.y
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click
                self.selected = False
                self.resize = False
        elif event.type == pygame.MOUSEMOTION:
            if self.selected:
                if self.resize:
                    new_width = max(200, event.pos[0] - self.rect.x - self.offset_x)
                    new_height = max(150, event.pos[1] - self.rect.y - self.offset_y)
                    if self.rect.x + new_width <= self.application.screen_width and self.rect.y + new_height <= self.application.screen_height - self.application.TASKBAR_HEIGHT:
                        self.rect.width = new_width
                        self.rect.height = new_height
                else:
                    new_x = min(max(0, event.pos[0] - self.offset_x), self.application.screen_width - self.rect.width)
                    new_y = min(max(0, event.pos[1] - self.offset_y), self.application.screen_height - self.rect.height - self.application.TASKBAR_HEIGHT)
                    self.rect.x = new_x
                    self.rect.y = new_y

    def minimize(self):
        """
        Minimizes the window and adds it to the taskbar.
        """
        self.minimized = True
        self.application.taskbar.add_window(self)

    def maximize(self):
        """
        Maximizes the window to fill the screen, storing the previous size and position.
        """
        self.prev_rect = self.rect.copy()
        self.rect = pygame.Rect(0, 0, self.application.screen_width, self.application.screen_height - self.application.TASKBAR_HEIGHT)
        self.maximized = True

    def restore(self):
        """
        Restores the window to its previous size and position.
        """
        self.rect = self.prev_rect.copy()
        self.minimized = False
        self.maximized = False
        self.application.taskbar.remove_window(self)

    def toggle_maximize(self):
        """
        Toggles between maximized and restored states.
        """
        if self.maximized:
            self.restore()
        else:
            self.maximize()

class MainMenuWindow(Window):
    """
    Represents the main context menu for a window, handling static and dynamic options with pagination.
    """
    OPTIONS_PER_PAGE = 5  # Number of dynamic options per page

    def __init__(self, x, y, target_window, application):
        self.static_options = [
            {'name': "RGB"},
            {'name': "Help"},
            {'name': "New Option"}
        ]  # Static menu options
        self.target_window = target_window
        self.application = application
        self.rect = pygame.Rect(x, y, 200, 0)  # Height is dynamically adjusted
        self.current_page = 0  # Start on the first page

    def draw_navigation_button(self, surface, label, rect, mouse_pos):
        """
        Draws a navigation button (e.g., next or previous page) within the menu.
        """
        pygame.draw.rect(surface, (180, 180, 180), rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2)
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, (150, 150, 150), rect)
        font = pygame.font.Font(None, 24)
        text = font.render(label, True, (0, 0, 0))
        text_x = rect.x + (rect.width - text.get_width()) // 2
        text_y = rect.y + (rect.height - text.get_height()) // 2
        surface.blit(text, (text_x, text_y))

    def draw(self, surface):
        """
        Draws the menu, including static and dynamic options, and pagination buttons if necessary.
        """
        visible_options = self.get_visible_options()
        actual_option_count = len(visible_options)

        max_option_height = (len(self.static_options) + self.OPTIONS_PER_PAGE) * 30
        self.rect.height = max_option_height + 50 if self.has_multiple_pages() else actual_option_count * 30 + 10

        pygame.draw.rect(surface, (200, 200, 200), self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)

        font_bold = pygame.font.Font(None, 28)
        font_regular = pygame.font.Font(None, 24)
        mouse_pos = pygame.mouse.get_pos()

        for i, option in enumerate(visible_options):
            option_rect = pygame.Rect(
                self.rect.x + 10,
                self.rect.y + 10 + i * 30,
                self.rect.width - 20,
                25
            )
            if option_rect.collidepoint(mouse_pos):
                pygame.draw.rect(surface, (150, 150, 150), option_rect)
            if option:
                # Bold font for static options
                if option['name'] in [opt['name'] for opt in self.static_options]:
                    font = font_bold
                else:
                    font = font_regular
                text = font.render(option['name'], True, (0, 0, 0))
                surface.blit(text, (option_rect.x + 5, option_rect.y + 2))

        if self.has_multiple_pages():
            prev_button_rect = pygame.Rect(self.rect.x + 10, self.rect.y + self.rect.height - 40, 60, 30)
            next_button_rect = pygame.Rect(self.rect.x + self.rect.width - 70, self.rect.y + self.rect.height - 40, 60, 30)
            self.draw_navigation_button(surface, "<-", prev_button_rect, mouse_pos)
            self.draw_navigation_button(surface, "->", next_button_rect, mouse_pos)

    def handle_event(self, event):
        """
        Handles events within the menu, such as option selection and pagination.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            visible_options = self.get_visible_options()
            for i, option in enumerate(visible_options):
                option_rect = pygame.Rect(
                    self.rect.x + 10,
                    self.rect.y + 10 + i * 30,
                    self.rect.width - 20,
                    25
                )
                if option and option_rect.collidepoint(event.pos):
                    if option['name'] == "RGB":
                        return RGBPropertiesWindow(event.pos[0], event.pos[1], self.target_window)
                    elif option['name'] == "Help":
                        return HelpWindow(event.pos[0], event.pos[1])
                    elif option['name'] == "New Option":
                        self.create_new_option()
                        return
                    else:
                        # Open an EditablePopupWindow for dynamic options
                        return EditablePopupWindow(event.pos[0], event.pos[1], self.target_window, option)
            if self.has_multiple_pages():
                prev_button_rect = pygame.Rect(self.rect.x + 10, self.rect.y + self.rect.height - 40, 60, 30)
                next_button_rect = pygame.Rect(self.rect.x + self.rect.width - 70, self.rect.y + self.rect.height - 40, 60, 30)
                if prev_button_rect.collidepoint(event.pos):
                    self.current_page = (self.current_page - 1) % self.get_total_pages()
                elif next_button_rect.collidepoint(event.pos):
                    self.current_page = (self.current_page + 1) % self.get_total_pages()
        return None

    def create_new_option(self):
        """
        Creates a new dynamic menu option and appends it to the target window's dynamic options.
        """
        new_option_number = len(self.target_window.dynamic_options) + 1
        new_option = {
            'name': f"Option {new_option_number}",
            'body': "Editable body text."
        }
        self.target_window.dynamic_options.append(new_option)
        self.current_page = self.get_total_pages() - 1  # Navigate to the last page where the new option is added

    def get_visible_options(self):
        """
        Retrieves the current set of visible options based on the current page.
        """
        start_index = self.current_page * self.OPTIONS_PER_PAGE
        end_index = start_index + self.OPTIONS_PER_PAGE
        dynamic_page = self.target_window.dynamic_options[start_index:end_index]
        return self.static_options + dynamic_page

    def has_multiple_pages(self):
        """
        Determines if pagination is necessary based on the number of dynamic options.
        """
        return len(self.target_window.dynamic_options) > self.OPTIONS_PER_PAGE

    def get_total_pages(self):
        """
        Calculates the total number of pages required for dynamic options.
        """
        return (len(self.target_window.dynamic_options) + self.OPTIONS_PER_PAGE - 1) // self.OPTIONS_PER_PAGE

class EditablePopupWindow(Window):
    """
    A popup window that allows users to edit the title and body of a dynamic menu option.
    Implements text wrapping while respecting manual line breaks.
    """
    def __init__(self, x, y, target_window, option):
        self.target_window = target_window
        self.option = option  # Now a dict with 'name' and 'body'
        self.title = self.option['name']  # Start with the option name as the title
        self.body = self.option['body']
        self.rect = pygame.Rect(x, y, 300, 200)
        self.font = pygame.font.Font(None, 24)

        # Editing states
        self.editing_title = False
        self.editing_body = False
        self.input_text = ""
        self.cursor_visible = True
        self.cursor_counter = 0

    def draw(self, surface):
        # Draw window
        pygame.draw.rect(surface, (220, 220, 220), self.rect, border_radius=5)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2, border_radius=5)

        # Draw title bar
        title_bar_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(surface, (100, 100, 250), title_bar_rect, border_radius=5)

        # Draw title text
        if self.editing_title:
            display_title = self.input_text
        else:
            display_title = self.title
        title_surf = self.font.render(display_title, True, (255, 255, 255))
        surface.blit(title_surf, (self.rect.x + 10, self.rect.y + 5))

        # Draw body text with wrapping
        if self.editing_body:
            display_body = self.input_text
        else:
            display_body = self.body

        # Split the body text by newline to respect manual line breaks
        body_lines = display_body.split('\n')
        wrapped_body = []
        for line in body_lines:
            wrapped_body.extend(textwrap.wrap(line, width=40))  # Adjust width as needed

        y_offset = self.rect.y + 40
        for line in wrapped_body:
            body_surf = self.font.render(line, True, (0, 0, 0))
            surface.blit(body_surf, (self.rect.x + 10, y_offset))
            y_offset += body_surf.get_height() + 5

        # Handle cursor for title
        if self.editing_title:
            self.cursor_counter += 1
            if self.cursor_counter >= 60:
                self.cursor_visible = not self.cursor_visible
                self.cursor_counter = 0
            if self.cursor_visible:
                cursor_x = self.rect.x + 10 + self.font.size(display_title)[0] + 2
                cursor_y = self.rect.y + 5
                pygame.draw.line(surface, (255, 255, 255), (cursor_x, cursor_y), (cursor_x, cursor_y + self.font.get_height()))

        # Handle cursor for body
        if self.editing_body:
            self.cursor_counter += 1
            if self.cursor_counter >= 60:
                self.cursor_visible = not self.cursor_visible
                self.cursor_counter = 0
            if self.cursor_visible:
                # Calculate cursor position based on input_text
                cursor_x = self.rect.x + 10 + self.font.size(display_body)[0] + 2
                cursor_y = self.rect.y + 40 + len(wrapped_body) * (self.font.get_height() + 5)
                pygame.draw.line(surface, (0, 0, 0), (cursor_x, cursor_y), (cursor_x, cursor_y + self.font.get_height()))

    def handle_event(self, event):
        """
        Handles user input for editing the title and body, implementing text wrapping.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if title is clicked
            title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
            if title_rect.collidepoint(event.pos):
                self.editing_title = True
                self.editing_body = False
                self.input_text = self.title
                return

            # Check if body is clicked
            body_rect = pygame.Rect(self.rect.x, self.rect.y + 30, self.rect.width, self.rect.height - 30)
            if body_rect.collidepoint(event.pos):
                self.editing_body = True
                self.editing_title = False
                self.input_text = self.body
                return

            # Clicked outside editable areas
            self.editing_title = False
            self.editing_body = False

        elif event.type == pygame.KEYDOWN:
            if self.editing_title or self.editing_body:
                if event.key == pygame.K_RETURN:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        # Shift+Enter: Add new line
                        if self.editing_body:
                            self.body += '\n'
                            self.input_text += '\n'
                    else:
                        # Enter: Lock in the text
                        if self.editing_title:
                            new_title = self.input_text
                            self.title = new_title
                            self.editing_title = False

                            # Update the dynamic options in the target window
                            self.option['name'] = new_title

                        elif self.editing_body:
                            self.body = self.input_text
                            self.editing_body = False
                            self.option['body'] = self.body

                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    self.input_text += event.unicode

    def update(self):
        """
        Update logic if necessary. Currently unused but can be expanded.
        """
        pass

class RGBPropertiesWindow(Window):
    """
    A popup window that allows users to adjust the RGB color properties of a target window.
    """
    def __init__(self, x, y, target_window):
        self.target_window = target_window
        self.r = 100
        self.g = 100
        self.b = 250
        self.labels = ["R", "G", "B"]
        font = pygame.font.Font(None, 24)
        self.text_lines = [
            "RGB Properties",
            "Adjust the color sliders below."
        ]
        # Calculate popup size based on text
        width, height = self.calculate_popup_size(self.text_lines, font)
        # Ensure minimum width to accommodate sliders
        width = max(width, 200)
        height += 80  # Space for sliders
        self.rect = pygame.Rect(x, y, width, height)
        self.sliders = {
            'R': pygame.Rect(x + 20, y + 60, 150, 20),
            'G': pygame.Rect(x + 20, y + 90, 150, 20),
            'B': pygame.Rect(x + 20, y + 120, 150, 20)
        }
        self.dragging = {'r': False, 'g': False, 'b': False}

    def calculate_popup_size(self, text_lines, font, padding=20):
        """
        Calculates the size of the popup window based on the text content.
        """
        max_width = 0
        total_height = padding * 2
        for line in text_lines:
            text_surface = font.render(line, True, (0, 0, 0))
            if text_surface.get_width() > max_width:
                max_width = text_surface.get_width()
            total_height += text_surface.get_height() + 5  # 5 pixels between lines
        return (max_width + padding * 2, total_height)

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 200, 200), self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        font = pygame.font.Font(None, 24)
        for i, line in enumerate(self.text_lines):
            text = font.render(line, True, (0, 0, 0))
            surface.blit(text, (self.rect.x + 10, self.rect.y + 10 + i * 30))
        for key, slider in self.sliders.items():
            pygame.draw.rect(surface, (180, 180, 180), slider)
            pygame.draw.rect(surface, (0, 0, 0), slider, 1)
            value = getattr(self, key.lower())
            pygame.draw.rect(
                surface,
                (0, 0, 0),
                (slider.x, slider.y, value / 255 * slider.width, slider.height)
            )
            label = font.render(f"{key}: {value}", True, (0, 0, 0))
            surface.blit(label, (slider.x + slider.width + 10, slider.y))

    def handle_event(self, event):
        """
        Handles interactions with the RGB sliders.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            for key, slider in self.sliders.items():
                if slider.collidepoint(event.pos):
                    self.dragging[key.lower()] = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left click
            for key in self.sliders.keys():
                self.dragging[key.lower()] = False
        elif event.type == pygame.MOUSEMOTION:
            for key, slider in self.sliders.items():
                if self.dragging.get(key.lower(), False):
                    new_value = min(max(0, event.pos[0] - slider.x), slider.width) / slider.width * 255
                    setattr(self, key.lower(), int(new_value))
                    self.update_color()

    def update_color(self):
        """
        Updates the color of the target window based on slider values.
        """
        self.target_window.color = (self.r, self.g, self.b)

class SubmenuWindow(Window):
    """
    Represents a submenu window with placeholder text.
    """
    def __init__(self, x, y, title):
        self.text_lines = [
            f"Submenu: {title}",
            "Placeholder text for the submenu.",
            "More information can be added here."
        ]
        font = pygame.font.Font(None, 24)
        width, height = self.calculate_popup_size(self.text_lines, font, padding=20)
        self.rect = pygame.Rect(x, y, width, height)

    def calculate_popup_size(self, text_lines, font, padding=20):
        """
        Calculates the size of the submenu window based on text content.
        """
        max_width = 0
        total_height = padding * 2
        for line in text_lines:
            text_surface = font.render(line, True, (0, 0, 0))
            if text_surface.get_width() > max_width:
                max_width = text_surface.get_width()
            total_height += text_surface.get_height() + 5  # 5 pixels between lines
        return (max_width + padding * 2, total_height)

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 200, 200), self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        font = pygame.font.Font(None, 24)
        render_text_list(surface, self.text_lines, font, self.rect)

    def handle_event(self, event):
        pass

class HelpWindow(Window):
    """
    Represents the help window displaying instructions and shortcuts.
    """
    def __init__(self, x, y):
        self.text_lines = [
            "Help Menu:",
            "1. Right-click on a window to open the context menu.",
            "2. Use the 'RGB' option to adjust the window's color dynamically.",
            "3. Use 'New Option' to create dynamic menu items.",
            "4. Use the taskbar to restore minimized windows.",
            "5. Drag a window by clicking and holding the title bar.",
            "6. Resize a window using the handle at the bottom-right corner.",
            "7. Use the 'Help' option to open this help menu.",
            "8. Keyboard Shortcuts:",
            "   - Ctrl+N: Open a new window.",
            "   - Ctrl+W: Minimize the selected window.",
            "   - Ctrl+F: Toggle fullscreen mode.",
            "9. Taskbar interaction: Minimized windows appear in the taskbar.",
            "   Click their buttons to restore them.",
            "10. Use the main menu for window-specific actions."
        ]
        font = pygame.font.Font(None, 24)
        width, height = self.calculate_popup_size(self.text_lines, font, padding=20)
        self.rect = pygame.Rect(x, y, width, height)

    def calculate_popup_size(self, text_lines, font, padding=20):
        """
        Calculates the size of the help window based on text content.
        """
        max_width = 0
        total_height = padding * 2
        for line in text_lines:
            text_surface = font.render(line, True, (0, 0, 0))
            if text_surface.get_width() > max_width:
                max_width = text_surface.get_width()
            total_height += text_surface.get_height() + 5  # 5 pixels between lines
        return (max_width + padding * 2, total_height)

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 200, 200), self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        font = pygame.font.Font(None, 24)
        render_text_list(surface, self.text_lines, font, self.rect)

    def handle_event(self, event):
        pass

if __name__ == "__main__":
    app = Application()
    main_window = DraggableWindow(100, 100, 300, 200, app, title="Main Window")
    app.window_manager.add_window(main_window)
    app.run()
