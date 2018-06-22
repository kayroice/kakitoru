#!/usr/bin/env python3

import datetime
import itertools
import jinja2
import logging
import os
import pytz
import shutil
import sys
import tempfile
import yaml


class NotesErr(Exception):
    pass


class NotesBase(object):

    def __init__(self, config_file=None, **kwargs):
        """
        Args:
            config_file (str): Path to notes config file in yaml format.
        """
        self.configs = self.get_configs(config_file, **kwargs)
        self.date = None

    @staticmethod
    def comment(comment=None):
        """
        Args:
            comment (str): Note comment.

        Returns:
            Returns a dict where the primary key is 'comment' and the value is
            comment passed into the method.
        """
        logging.debug("Note comment defined as: {}".format(comment))
        return {'comment': comment}

    @staticmethod
    def content(content=None):
        """
        Args:
            content (str): Note content.

        Returns:
            Returns a dict where the primary key is 'content' and the value is
            content passed into the method.
        """
        logging.debug("Note content defined as: {}".format(content))
        return {'content': content}

    def content_type(self, content_type=None):
        """
        The content type for the markdown content (code block). See also:
        https://help.github.com/articles/creating-and-highlighting-code-blocks

        Args:
            content_type (str): The markdown content type, defaults to 'text'.

        Returns:
            Returns the content type as a string.
        """
        content_type = content_type or self.configs['default_content_type']
        logging.debug("Content type defined as: {}".format(content_type))
        return content_type

    def render_note(self, template_file=None, note=None, content_type=None):
        """
        Using the specified template file interpolate the note dict and render
        the template.

        Args:
            template_file (str): Path to Jinja2 template file.
            note (dict): Note data.
            content_type (str): Type of syntax highlighting to use with note
                                content.

        Returns:
            Returns the call to self.render_template as a string object.
        """
        content_type = self.content_type(content_type)
        note = note or self.note()
        template_file = self.template_file(template_file)
        msg = "Creating markdown using {} for: {}".format(template_file, note)
        logging.debug(msg)
        template = self.get_template(template_file)
        template_data = {'note': note, 'content_type': content_type}
        return self.render_template(template, template_data)

    @staticmethod
    def create_tmp_file(prefix, suffix, delete=False):
        """
        Create a temporary file.

        Args:
            prefix (str): Prefix for the temp file name.
            suffix (str): Suffix for the temp file name.
            delete (bool): If set to True will delete the temp file after its
                file descriptor has been closed, defaults to False.

        Return:
            Returns a tempfile file object.
        """
        try:
            tmp_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix,
                                                   delete=delete)
            logging.debug("Created temp file: {}".format(tmp_file.name))
            return tmp_file
        except Exception as e:
            msg = "Unable to create temp file: {}".format(str(e))
            raise NotesErr(msg)

    @staticmethod
    def current_datetime(timezone=None):
        """
        Get a datetime object for the current time (now). See:
        https://docs.python.org/3/library/datetime.html

        tz (str): Time zone, defaults to 'US/Pacific', for a complete list
                  check pytz.common_timezones.

        Returns:
            Returns a datetime object for the current time.
        """
        timezone = timezone or 'US/Pacific'
        pst = pytz.timezone(timezone)
        return datetime.datetime.now(pst)

    @staticmethod
    def dir_exists(dirname=None):
        if not os.path.isdir(dirname):
            logging.error("Directory does not exist: {}".format(dirname))
            return False
        return True

    @staticmethod
    def flattened_list(nested_list):
        """
        Flatten the given list.

        Args:
            nested_list (list): A list object to be flattened.

        Returns:
            Returns a flattened list.
        """
        logging.debug("Flattening list: {}".format(nested_list))
        flattened_list = []
        for element in nested_list:
            flattened_list.append(element)
        # Flatten the list as we may have passed in a list as an arg such as
        # when passing in a list of args from argparse on the cli.
        return list(itertools.chain(*flattened_list))

    def get_configs(self, config_file=None, **kwargs):
        default_config_filename = '.notes_config.yaml'
        config_file = config_file or default_config_filename
        logging.debug("Notes config file defined as {}".format(config_file))
        try:
            configs = self.get_yaml_data(config_file) or {}
        except Exception as e:
            msg = "Unable to get config data from {}: {}".format(config_file, e)
            raise NotesErr(msg)
        for key, value in kwargs.items():
            configs.update({key: value})
        logging.debug("Configs defined as: {}".format(configs))
        return configs

    def get_date(self):
        """
        Converts the current datetime object into a string and returns a string.
        See:
        https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

        Returns:
            Returns a string of the current time.
        """
        date = self.current_datetime().strftime('%a %b %d %H:%M:%S %Z %Y')
        logging.debug("Date defined as: {}".format(date))
        return date

    def get_input(self, buffer_size=4096):
        """
        Get input from user and return its contents. If the caller is a tty
        then call self.get_user_input, otherwise read from stdin.

        Args:
            buffer_size (int): The size of the input buffer, defaults to 4096.

        Returns:
            Returns a string of the content that is read.
        """
        if sys.stdin.isatty():
            content = self.get_user_input(buffer_size)
        else:
            content = ''
            for line in sys.stdin.readlines(buffer_size):
                content += line
        return content

    def get_template(self, template_file):
        """
        Get the Jinja2 template object given a template file.

        Args:
            template_file (str): Path to Jinja2 template file.

        Returns:
            Returns the jinja2.Template object.
        """
        template_contents = self.read_file(template_file)
        msg = "Building template object from file: {}".format(template_file)
        logging.debug(msg)
        try:
            template = jinja2.Template(template_contents)
            template.name = template_file
            return template
        except Exception as e:
            msg = "Failed to read template {}: {}".format(template_file, e)
            raise NotesErr(msg)

    @staticmethod
    def get_user_input(buffer_size=4096):
        """
        Prompt the user for input. Breaks on 'EOF', '.', or CTRL-D.

        Args:
            buffer_size (int): Size of the input buffer, defaults to 4096.

        Returns:
            Returns the user's input as a string.
        """
        user_input = ''
        print("Press CTRL-D (^D) or send 'EOF' to terminate input...")
        while True:
            try:
                input_buffer = sys.stdin.readline(buffer_size)
                if input_buffer in ['EOF\n', '.\n', '']:
                    break
            except EOFError:
                break
            except KeyboardInterrupt:
                print("ERROR: caught CTRL-C (^C), skipping note creation.")
                sys.exit(1)
            user_input += input_buffer
        return user_input

    @staticmethod
    def get_yaml_data(yaml_file):
        """
        Read a yaml file and load its data.

        Args:
            yaml_file (str): Yaml file to be loaded.

        Returns:
            Returns a dict of the loaded yaml data.
        """
        if not os.path.exists(yaml_file):
            logging.error("File not found: {}".format(yaml_file))
            return None
        try:
            logging.debug("Reading file: {}".format(yaml_file))
            with open(yaml_file, 'r') as yaml_fd:
                yaml_data = yaml.safe_load(yaml_fd)
                logging.debug("Successfully parsed: {}".format(yaml_file))
                return yaml_data
        except Exception as e:
            logging.error("Unable to read {}: {}".format(yaml_file, e))
        return None

    def header(self, header=None):
        """
        The header object. If header is defined then the format of the header
        will be:

        $header / $current_date

        If header is not specified then only the current date will be used.

        Args:
            header (str): Header to be used.

        Returns:
            Returns a dict where the key is 'header' and the value is a string
            containing the specified header and current time.
        """
        if header:
            if self.configs['append_date_to_header']:
                header = "{} / {}".format(header, self.date)
        else:
            header = self.date
        logging.debug("Header defined as: {}".format(header))
        return {'header': header}

    def note(self, date=None, comment=None, content=None, tags=None, urls=None,
             header=None, **kwargs):
        """
        Build a note object.

        Returns:
            Returns a dict of the note.
        """
        self.date = date or self.get_date()
        note = {}
        comment = self.comment(comment)
        content = self.content(content)
        header = self.header(header)
        tags = self.tags(tags)
        urls = self.urls(urls)
        for element in [comment, content, header]:
            for value in element.values():
                if value:
                    note.update(element)
                    continue
        if tags['tags']:
            note.update(tags)
        if urls['urls']:
            note.update(urls)
        for key, value in kwargs.items():
            note.update({key: value})
        logging.debug("Note defined as: {}".format(note))
        return note

    def notes_file(self, notes_file=None):
        if notes_file:
            pass
        elif 'notes_file' in self.configs.keys():
            notes_file = self.configs['notes_file']
        else:
            raise NotesErr("Path to notes file not defined.")
        notes_dir = os.path.dirname(notes_file)
        if not self.dir_exists(notes_dir):
            msg = "Notes file's directory does not exist: {}".format(notes_dir)
            raise NotesErr(msg)
        return notes_file

    def prepend_data_to_file(self, filename, data):
        """
        Prepend date to a file. First creates a temp file to write data to.
        Next, if the named file exists read from the file, then write its
        data to the newly created temp file. Finally, rename the temp file to
        the named file.

        Args:
            data: Data to write to the file.
            filename (str): Path to filename to write to.

        Returns:
            Returns True if successful.
        """
        # First create a temp file, and then write our data to the file.
        tmp_file = self.create_tmp_file('notes.', '.md', delete=False)
        self.write_data_to_file(tmp_file.name, data)
        # If the destination file exists we'll read from it, and then append
        # its data to the new temp file.
        if os.path.exists(filename):
            notes_data = self.read_file(filename)
            self.write_data_to_file(tmp_file.name, notes_data)
        # Now rename the temp file to the destination file.
        self.rename_file(tmp_file.name, filename)
        return True

    @staticmethod
    def read_file(filename):
        """
        Read the contents of the given file.

        Args:
            filename (str): Path to file to read.

        Returns:
            Returns the contents of the given file as a string object.
        """
        try:
            logging.debug("Reading file: {}".format(filename))
            with open(filename, 'r') as filename_fd:
                return filename_fd.read()
        except Exception as e:
            msg = "Failed to read file {}: {}".format(filename, e)
            raise NotesErr(msg)

    @staticmethod
    def rename_file(src_file, dest_file):
        """
        Rename the source file to the destination file by calling shutil.move.

        Args:
            src_file (str): Path to source file.
            dest_file (str): Path to destination file (new file name).

        Returns:
            Returns a bool based on whether the rename was successful.
        """
        try:
            logging.debug("Renaming {} to {}".format(src_file, dest_file))
            shutil.move(src_file, dest_file)
            return True
        except Exception as e:
            msg = "Failed to rename {} to {}: {}".format(src_file, dest_file, e)
            raise NotesErr(msg)
        return False

    @staticmethod
    def render_template(template, template_data=None):
        """
        Render the given Jinja2 template object, and interpolate any template
        data passed as an arg.

        Args:
            template (jinja2.Template): The Jinja2 template object.
            template_data (dict): A dictionary to use when rendering the
                                  template.

        Returns:
            Returns the contents of the rendered template as a string.
        """
        template_data = template_data or {}
        try:
            msg = "Rendering template {} with data: {}".format(template.name,
                                                               template_data)
            logging.debug(msg)
            template_contents = template.render(template_data)
            return template_contents
        except Exception as e:
            msg = "Failed to render template {} with data {}: {}".format(
                template.name, template_data, e)
            raise NotesErr(msg)

    def tags(self, tags=None):
        """
        Args:
            tags: Pass in a list of tags.

        Returns:
            Returns a list of tags.
        """
        tags = tags or []
        for idx, tag in enumerate(tags):
            if not type(tag) == str:
                tags[idx] = str(tag)
            if self.configs['auto_prepend_hashtag']:
                if not tag.startswith("#"):
                    tags[idx] = "#{}".format(tag)
        logging.debug("Tags defined as: {}".format(tags))
        return {'tags': tags}

    def template_file(self, template_file=None):
        """
        Define the template file to be used.

        Args:
            template_file (str): Path to template file. If None then use the
            config value 'default_template_file'.

        Returns:
            Returns the path to the template file as a string if the file
            exists.
        """
        template_file = template_file or self.configs['default_template_file']
        logging.debug("Template file defined as: {}".format(template_file))
        if os.path.exists(template_file):
            return template_file
        else:
            msg = "Template file {} not found.".format(template_file)
            raise NotesErr(msg)

    def take_note(self, note, notes_file=None, append=False, content_type=None,
                  template_file=None, dryrun=False):
        """
        """
        notes_file = notes_file or self.notes_file(notes_file)
        rendered_note = self.render_note(template_file, note, content_type)
        if dryrun:
            return rendered_note
        if append:
            return self.write_data_to_file(notes_file, rendered_note)
        else:
            return self.prepend_data_to_file(notes_file, rendered_note)
        msg = "Failed to write note {} to: {}".format(note, notes_file)
        logging.error(msg)
        return None

    @staticmethod
    def urls(urls=None):
        """
        Args:
            url (str): Note url.

        Returns:
            Returns a dict where the primary key is 'url' and the value is
            url passed into the method.
        """
        urls = urls or []
        logging.debug("URLs defined as: {}".format(urls))
        return {'urls': urls}

    @staticmethod
    def write_data_to_file(filename, data):
        """
        """
        # If the file exists then we'll append our data to it, otherwise we'll
        # create a new file (with the 'w' arg to the 'open' func).
        write_arg = 'a' if os.path.exists(filename) else 'w'
        try:
            logging.debug("Writing to file: {}".format(filename))
            with open(filename, write_arg) as filename_fd:
                filename_fd.write(data)
            return True
        except Exception as e:
            msg = "Failed to write to {}: {}".format(filename, e)
            raise NotesErr(msg)
        return False
