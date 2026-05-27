from tclCommands.TclCommand import *


class TclCommandWriteGCode(TclCommandSignaled):
    """
    Tcl shell command to save the G-code of a CNC Job object to file.
    """

    # array of all command aliases, to be able use
    # old names for backward compatibility (add_poly, add_polygon)
    aliases = ['write_gcode']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str),
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('preamble', str),
        ('postamble', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Saves G-code of a CNC Job object to file.",
        'args': collections.OrderedDict([
            ('name', 'Source CNC Job object.'),
            ('filename', 'Output filename.'),
            ('preamble', 'Text to append at the beginning.'),
            ('postamble', 'Text to append at the end.')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        """
        Requires obj_name to be available. It might still be in the
        making at the time this function is called, so check for
        promises and send to background if there are promises.
        """

        obj_name = args['name']
        filename = args['filename']

        preamble = args['preamble'] if 'preamble' in args else ''
        postamble = args['postamble'] if 'postamble' in args else ''

        # TODO: This is not needed any more? All targets should be present.

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except:
            return "Could not retrieve object: %s" % obj_name

        try:
            obj.export_gcode(str(filename), str(preamble), str(postamble))
        except Exception as e:
            return "Operation failed: %s" % str(e)
