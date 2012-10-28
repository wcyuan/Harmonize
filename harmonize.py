#!/usr/bin/env python
"""
harmonize.py [<options>] [note]*

Description: Module for music notation and harmonization.  

This script provides a list of possible chord harmonizations for a
given melody.  Given a melody (just a list of notes with no rhythm),
it print out a list of harmonizations.  Each harmonization is a list
of chords, one per note.  It doesn't attempt to show the appropriate
voicing for the chord.

The algorithm is pretty simple, there is a hard-coded list of
acceptable chord progressions, so we just step through the melody and
apply each possible progression that matches the melody.

This file also contains constants and classes for a general music
notation package.  There are three classes provided: Note,
Interval, and Chord.  So far these classes only represent
pitches, no rhythm or other musical features (e.g. keys, time
signatures, scales, dynamics, voices, etc).

A Note encapsulates three core pieces of information: the letter
name of the pitch, an accidental, and the octave of the pitch.  An
Interval is really has the same properties as a Note, but it is
used differently.  A Chord is essentially a Note, plus a list of
Intervals.

Wishlist: 
 - add comments
 - add probabilities for transitioning to a chord and a key
 - fit those probabilities (bach chorales are available from music21 project)

Created by: Conan Yuan (yuanc), 20111218

"""
#
# Imports
#

from __future__ import division, absolute_import, with_statement
from logging    import debug, getLogger, getLevelName
from optparse   import OptionParser
from math       import floor
from functools  import update_wrapper 
from contextlib import contextmanager
import re

##################################################################

def logat(level=None):
    '''
    A helper function for setting the log level of the module.  

    level: The level to log at.  Should either be the name of a level,
           or the integer representation of the level.  For valid values,
           see the logging module.
    '''
    if level is None:
        lvl = getLogger().level
        if isinstance(lvl, int):
            return getLevelName(lvl)
        else:
            return lvl
    else:
        if not isinstance(level, int):
            level = getLevelName(level)
        getLogger().setLevel(level)
        print "Set logger for {0} to {1}".format(getLogger().name, logat())

##################################################################

# This is a list of all the constants and classes which are exported
# by default.  We export the Note, Chord, and Interval classes, and
# the corresponding constants.  We also export the list of common
# progressions and cadences.
__all__ = ['Note',
           'C'  ,
           'Cb' ,
           'Cs' ,
           'Db' ,
           'D'  ,
           'Ds' ,
           'Eb' ,
           'E'  ,
           'Es' ,
           'Fb' ,
           'F'  ,
           'Fs' ,
           'Gb' ,
           'G'  ,
           'Gs' ,
           'Ab' ,
           'A'  ,
           'As' ,
           'Bb' ,
           'B'  ,
           'Bs' ,

           'Interval',
           'U'  ,
           'd2' ,
           'm2' ,
           'M2' ,
           'A2' ,
           'd3' ,
           'm3' ,
           'M3' ,
           'A3' ,
           'd4' ,
           'P4' ,
           'A4' ,
           'd5' ,
           'P5' ,
           'A5' ,
           'd6' ,
           'm6' ,
           'M6' ,
           'A6' ,
           'd7' ,
           'm7' ,
           'M7' ,
           'A7' ,
           'O'  ,

           'Chord',
           'Cmaj',
           'Cmin',
           'Cdim',
           'Caug',
           'Dmaj',
           'Dmin',
           'Ddim',
           'Daug',
           'Emaj',
           'Emin',
           'Edim',
           'Eaug',
           'Fmaj',
           'Fmin',
           'Fdim',
           'Faug',
           'Gmaj',
           'Gmin',
           'Gdim',
           'Gaug',
           'Amaj',
           'Amin',
           'Adim',
           'Aaug',
           'Bmaj',
           'Bmin',
           'Bdim',
           'Baug',
           'I'  ,
           'ii' ,
           'iii',
           'IV' ,
           'V'  ,
           'vi' ,
           'vii',

           'PROGRESSIONS',
           'CADENCES'
           ]

##################################################################

class FrozenClass(object):
    '''
    Subclasses of this class can use the _freeze method to disallow
    further changes to the object after the object has been
    initialized.

    The _unfrozen method is also provided, to allow exceptions.  
    '''

    # This controls whether setting attributes is allowed.  
    __is_frozen = False


    def __setattr__(self, key, value):
        '''
        We allow attributes to be set if and only if the object is not
        frozen.
        '''
        if self.__is_frozen:
            raise TypeError( "%r is a frozen class" % self )
        object.__setattr__(self, key, value)

    def __delattr__(self, k):
        '''
        We allow attributes to be deleted if and only if the object is
        not frozen.
        '''
        if self.__is_frozen:
            raise TypeError( "%r is a frozen class" % self )
        del self.__dict__[k]

    def _freeze(self):
        '''
        Call _freeze to disallow further attribute updates.  
        '''
        self.__is_frozen = True

    @contextmanager
    def _unfrozen(self):
        """
        Context manager that temporarily allows adding new attributes inside
        the context.
        """
        old_frozen = self.__is_frozen
        try:
            # We have to access __dict__ directly in order to bypass
            # the restrictions in the __setattr__ method.
            self.__dict__['_FrozenClass__is_frozen'] = False
            yield
        finally:
            self.__dict__['_FrozenClass__is_frozen'] = old_frozen

##################################################################

class cached_attribute(object):
    """
    Cached attribute access for instances (Based on ActiveState recipe
    276643).  cached_attribute knows how to work with FrozenClass.  
    
    http://code.activestate.com/recipes/276643-caching-and-aliasing-with-descriptors/history/1/

    >>> class C(object):
    ...    @cached_attribute
    ...    def a(self):
    ...        print 'computing...'
    ...        return 1 + 1
    >>>
    >>> c = C()
    >>> c.__dict__
    {}
    >>>
    >>> type(C.a)
    <class '__main__.cached_attribute'>
    >>>
    >>> c.a
    computing...
    2
    >>>
    >>> c.__dict__
    {'a': 2}
    >>>
    >>> c.a
    2

    """
    def __init__(self, method, name=None):
        self.method = method
        self.name   = name or method.__name__
        update_wrapper(self, method)

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        result = self.method(inst)
        if isinstance(inst, FrozenClass):
            with inst._unfrozen():
                setattr(inst, self.name, result)
        else:
            setattr(inst, self.name, result)
        return result

##################################################################

class Note(FrozenClass):
    """
    A note has these attributes
      name       -  the letter name of the note ('A', to 'G')
      accidental -  the number of half steps from the note.  1 is
                    sharp, -1 is flat, 2 is double sharp, -2 is 
                    double flat, etc
      octave     -  a number indicating which octave we are in.  
                    0 is the octave of middle C

    From those attributes, we can compute these properties, which
    should be considered implementation details, not formally part of
    the Note API.  We define them here to make the code easier to
    read.

      steps      -  number of halfsteps away from middle C.  

      scale_num  -  a numeric representation of the name and octave
                    Middle 'C' is 0, 'D' is 1, etc., 'B' is 6.  
                    'C' in octave 1 is scale_num 7, etc.  

                    Scale num isn't a great name, since that suggests
                    that it could change when we change keys.  In
                    fact, we just need a numeric representation so we
                    can do arithmetic between Notes, so the scale_num
                    is the same no matter what key we are in, or you
                    could say that we insist on the key of C.

    The main features of a Note are Note arithmetic, and translation
    to and from a string representation.  The string representation
    simply concatenates the note name ('A' to 'G'), the accidental
    symbol and the octave number.

    The octave number is an integer.  Octave 0 is the octave of middle
    C.  Higher numbers represent higher octaves, lower numbers
    represent lower octaves.

    The accidental symbol is the empty string, if the accidental is
    zero, # for sharp, x for double sharp, b for flat, and bb for
    double flat.  All other accidentals are represented as integers
    (the number of half steps).  An integer accidental is ambiguous
    when it is followed by an integer octave (if the octave is
    positive, there is no way to know where the accidental ends and
    the octave begins).  But the assumption is that accidentals
    outside of [-2,2] are rare, plus this string representation is
    just for convenience -- you shouldn't assume that the string
    representation is reversible.  

    """

    # --------------------------------------------------------- #
    # Note: Class Attributes
    #

    __is_frozen = False

    _NOTE_ORDER = ('C', 'D', 'E', 'F', 'G', 'A', 'B')
    _STEPS_PER_OCTAVE = 12
    _NOTES_PER_OCTAVE = len(_NOTE_ORDER)
    _ACCIDENTAL_SYMS = ('bb', 'b', '', '#', 'x')

    isotonic_is_equal = True

    # --------------------------------------------------------- #
    # Note: Class Methods
    #

    @classmethod
    def _steps_to_scale_num(cls, steps, flat=False):
        """
        Convert from steps to a tuple containing (scale number,
        accidental, octave).

        Steps represents an integer number of half steps away from
        middle C.

        The scale number is a numeric representation of the C scale
        where 0 is middle C, 1 is D, etc.

        When converting from steps to scale num, you will either land
        exactly on a note of a scale, or you will be between two
        notes.  If the steps are between two notes, this method will
        return the lower note, plus an accidental of 1 to indicate a
        sharp.  If the argument 'flat' is True, then when the steps
        are between two notes, this method will return the higher
        note, plus an accidental of -1 to indicate a flat.

        >>> Note._steps_to_scale_num(4)
        (2, 0, 0)
        >>> Note._steps_to_scale_num(5)
        (3, 0, 0)
        >>> Note._steps_to_scale_num(6)
        (3, 1, 0)
        >>> Note._steps_to_scale_num(12)
        (0, 0, 1)
        >>> Note._steps_to_scale_num(13)
        (0, 1, 1)
        >>> Note._steps_to_scale_num(15)
        (1, 1, 1)
        >>> Note._steps_to_scale_num(-1)
        (6, 0, -1)
        >>> Note._steps_to_scale_num(-2)
        (5, 1, -1)
        >>> Note._steps_to_scale_num(-2, flat=True)
        (6, -1, -1)
        >>> Note._steps_to_scale_num(-12)
        (0, 0, -1)
        >>> Note._steps_to_scale_num(-24)
        (0, 0, -2)
        """

        # The algorithm is basically this: There are twelve notes per
        # octave, and each note of the scale corresponds to two half
        # steps.  So the octave is steps/12, scale_num is
        # ((steps%12)/2), and accidental is ((steps%12)%2).  However,
        # we have to account for the fact that there is only one half
        # step between E-F, and the "flat" option.

        octave = int(floor(steps / cls._STEPS_PER_OCTAVE))
        adj_steps = steps % cls._STEPS_PER_OCTAVE

        # Adding one half step to 5 or higher accounts for the fact
        # that there is only one half step between E and F.
        if adj_steps >= 5:
            adj_steps += 1
        scale_num = int(adj_steps / 2)
        if adj_steps % 2 == 0:
            accidental = 0
        elif flat:
            scale_num += 1
            accidental = -1
        else:
            accidental = 1
        #debug("steps %d -> adj_steps %d, scale_num %d, accidental %d" %
        #      (steps, adj_steps, scale_num, accidental))
        return (scale_num, accidental, octave)

    @classmethod
    def _scale_num_to_steps(cls, scale_num, accidental=0, octave=0):
        """
        Convert from scale_num (with an optional accidental and
        octave) to the number of half steps away from middle C.  

        >>> Note._scale_num_to_steps(1)
        2
        >>> Note._scale_num_to_steps(5)
        9
        >>> Note._scale_num_to_steps(7)
        12
        >>> Note._scale_num_to_steps(8)
        14
        >>> Note._scale_num_to_steps(12)
        21
        >>> Note._scale_num_to_steps(-1)
        -1
        >>> Note._scale_num_to_steps(-2)
        -3
        >>> Note._scale_num_to_steps(-3)
        -5
        >>> Note._scale_num_to_steps(-7)
        -12
        >>> Note._scale_num_to_steps(-8)
        -13
        """
        octave += int(floor(scale_num / cls._NOTES_PER_OCTAVE))
        steps = int(scale_num % cls._NOTES_PER_OCTAVE) * 2
        # Account for the fact that E-F is a single half step.  
        if scale_num % cls._NOTES_PER_OCTAVE > 2:
            steps -= 1
        steps += octave * cls._STEPS_PER_OCTAVE
        steps += accidental
        return steps

    @classmethod
    def _scale_num_to_name(cls, scale_num):
        """
        Convert from the numeric representation of a note (0-6) to the
        letter representation (A-G).
        
        >>> Note._scale_num_to_name(1)
        ('D', 0)
        >>> Note._scale_num_to_name(3)
        ('F', 0)
        >>> Note._scale_num_to_name(5)
        ('A', 0)
        >>> Note._scale_num_to_name(12)
        ('A', 1)
        >>> Note._scale_num_to_name(-1)
        ('B', -1)
        >>> Note._scale_num_to_name(-3)
        ('G', -1)
        >>> Note._scale_num_to_name(-7)
        ('C', -1)
        >>> Note._scale_num_to_name(-8)
        ('B', -2)
        """
        octave = int(floor(scale_num / cls._NOTES_PER_OCTAVE))
        return (cls._NOTE_ORDER[int(scale_num % cls._NOTES_PER_OCTAVE)], octave)

    @classmethod
    def _scale_name_to_num(cls, scale_name, octave=0):
        """
        Convert from the letter representation of a note (A-G) to the
        numeric representation (0-6).

        >>> Note._scale_name_to_num('C')
        0
        >>> Note._scale_name_to_num('C', octave=-1)
        -7
        >>> Note._scale_name_to_num('E', octave=1)
        9
        >>> Note._scale_name_to_num('E', octave=-1)
        -5
        >>> Note._scale_name_to_num('A')
        5
        """
        return (cls._NOTE_ORDER.index(scale_name.upper()) +
                octave * cls._NOTES_PER_OCTAVE)

    @classmethod
    def _name_to_steps(cls, name, accidental=0, octave=0):
        """
        Convert from the letter representation of a note (A-G) to the
        numeric representation (0-6).

        >>> Note._name_to_steps('E')
        4
        >>> Note._name_to_steps('E', accidental=1)
        5
        >>> Note._name_to_steps('E', accidental=1, octave=1)
        17
        >>> Note._name_to_steps('E', accidental=1, octave=-1)
        -7
        >>> Note._name_to_steps('A', accidental=1, octave=-1)
        -2
        >>> Note._name_to_steps('A', accidental=1, octave=0)
        10
        """
        scale_num = cls._scale_name_to_num(name)
        steps = cls._scale_num_to_steps(scale_num)
        steps += accidental
        steps += octave * cls._STEPS_PER_OCTAVE
        return steps

    @classmethod
    def _str_name(cls, name, accidental=0, octave=0):
        if 0 <= accidental+2 < len(cls._ACCIDENTAL_SYMS):
            accidental = cls._ACCIDENTAL_SYMS[accidental+2]
        elif accidental > 0:
            accidental = '+' + str(accidental)
        # putting octave right after accidental makes things confusing
        # if accidental is not between -2 and 2 and is represented as
        # a number.
        return "%s%s%d" % (name, accidental, octave)

    @classmethod
    def _parse_short_name(cls, shorthand):
        """
        >>> Note._parse_short_name('A')
        ('A', 0, 0)
        >>> Note._parse_short_name('A1')
        ('A', 0, 1)
        >>> Note._parse_short_name('A#1')
        ('A', 1, 1)
        >>> Note._parse_short_name('A#-1')
        ('A', 1, -1)
        """
        match = re.match('^(?:(\D)|(\d+))((?:|#|b|x|bb|\-\d+|\+\d+))((?:-|\+|)\d*)$', shorthand)
        if match is None:
            raise ValueError("Can't parse " + shorthand)

        #debug("Parsing %s as %s" % (shorthand, match.groups()))

        # accidental
        accidental_sym = match.group(3)
        if accidental_sym in cls._ACCIDENTAL_SYMS:
            accidental = cls._ACCIDENTAL_SYMS.index(accidental_sym) - 2
        else:
            accidental = int(accidental_sym)

        # octave
        if match.group(4) == "":
            octave = 0
        else:
            octave = int(match.group(4))

        # name or scale_num
        if match.group(1) is not None:
            name = match.group(1)
        else:
            scale_num = int(match.group(2))
            (name, this_octave) = cls._scale_num_to_name(scale_num)
            octave += this_octave

        return (name, accidental, octave)

    # --------------------------------------------------------- #
    # Note: CTOR
    #

    def __init__(self, 
                 short=None,
                 name=None, accidental=None, octave=None, 
                 scale_num=None, 
                 steps=None, 
                 flat=False, sharp=False, 
                 isotonic=None):
        super(Note, self).__init__()
        if short is not None:
            if (name is not None or
                scale_num is not None or
                steps is not None):
                raise ValueError("Cannot specify short with name, scale_num, or steps")
            if isinstance(short, Note):
                name = short.name
                accidental = short.accidental
                octave = short.octave
            else:
                (name, accidental, octave) = self._parse_short_name(short)

        if (name is not None or scale_num is not None):
            # set octave (may be changed when reading scale_num)
            if octave is None:
                octave = 0
            self.octave = octave

            # set name
            if scale_num is not None:
                (this_name, this_octave) = self._scale_num_to_name(scale_num)
                if name is not None and name != this_name:
                    raise ValueError("Name %s doesn't match scale num %d" % (name, scale_num))
                name = this_name
                # If the user specifies a scale_num and an octave, we
                # add the octaves together rather than expect them to
                # match.  This is so that scale_num=3, octave=1 is
                # allowed and means F1.
                self.octave += this_octave
            if name is not None:
                self.name = name

            # set accidental
            if accidental is None:
                if flat:
                    accidental = -1
                elif sharp:
                    accidental = 1
                else:
                    accidental = 0
            self.accidental  = accidental
            if steps is not None and steps != self.steps:
                raise ValueError("Name %s has steps %d not %d" %
                                 (self._str_name(name, accidental, octave),
                                  self.steps, steps))
        else:
            if steps is None:
                raise ValueError("Must specify note name or steps")
            if (accidental is not None or octave is not None):
                raise ValueError("Cannot specify accidental or octave without specifying the note name")
            (scale_num, myaccidental, myoctave) = self._steps_to_scale_num(steps)
            self.name = self._scale_num_to_name(scale_num)[0]
            self.accidental = myaccidental
            self.octave = myoctave

        if isotonic is not None:
            self.isotonic_is_equal = isotonic

        self._freeze()

    # --------------------------------------------------------- #
    # Note: Properties
    #

    @property
    def scale_num(self):
        return self._scale_name_to_num(self.name, self.octave)

    @property
    def steps(self):
        return self._name_to_steps(self.name, self.accidental, self.octave)

    # --------------------------------------------------------- #
    # Note: Methods
    #

    def __repr__(self):
        return "%s:%s" % (self.__class__.__name__, str(self))

    def __str__(self):
        return self._str_name(self.name, self.accidental, self.octave)

    def __eq__(self, other):
        if self.isotonic_is_equal and other.isotonic_is_equal:
            return self.steps == other.steps
        return (self.name == other.name and 
                self.accidental == other.accidental and
                self.octave == other.octave)

    def __cmp__(self, other):
        if self.isotonic_is_equal and other.isotonic_is_equal:
            return cmp(self.steps, other.steps)
        else:
            # If comparisons aren't based on the tone, but are based
            # on the note name, then we say that any version of a
            # higher note name is higher than any version of a lower
            # note name.  So Ab is higher than Gs, and Abb is higher
            # than Gx, which may be counterintuitive.
            #
            # We do this to preserve the relationship that all notes
            # must be either <, >, or =.  Otherwise, we could get the
            # situation where Ab and Gs are not equal, greater than,
            # or less than each other.
            retval = cmp(self.scale_num, other.scale_num)
            if retval != 0:
                return retval
            else:
                return cmp(self.accidental, other.accidental)

    def __hash__(self):
        if self.isotonic_is_equal:
            return hash(self.steps)
        return hash((self.name, self.accidental, self.octave))

    def __add__(self, other):
        """
        You should really add a note and an interval.  If you add a
        note to a note, we treat the second note as the interval
        between middle C and that Note.  This gives you the weird
        ability to add negative intervals, but adding Notes below
        middle C.

        >>> C + D
        Note:D0
        >>> G+P4
        Note:C1
        >>> A+E
        Note:C#1
        >>> Note('A-1') + P4
        Note:D0
        >>> Note('A-1') + Note('Ab-1')
        Note:F-1
        >>> B + Note('Ab-1')
        Note:G0
        >>> Note('Ab3') + M7
        Note:G4
        """
        if not isinstance(other, Note):
            return self + Interval(steps=other)

        # Note     + Note     = Note
        # Note     + Interval = Note
        # Interval + Note     = Interval
        # Interval + Interval = Interval
        scale_num = self.scale_num + other.scale_num
        accidental = self.steps + other.steps - self._scale_num_to_steps(scale_num)
        if isinstance(self, Interval):
            return Interval(distance=scale_num, accidental=accidental)
        else:
            return Note(scale_num=scale_num, accidental=accidental)

    def __sub__(self, other):
        """
        When you subtract two Notes, or if you subtract two Intervals,
        you get an Interval.  Intervals are always positive, so this
        function is associative: if you subtract E - G, you get the
        same thing as subtracting G - E.

        >>> Ab - C
        Interval:m6
        >>> B - E
        Interval:P5
        >>> E - B
        Interval:P5
        >>> G - E
        Interval:m3
        >>> G - Eb
        Interval:M3
        >>> G - M3
        Note:Eb0
        >>> C - P4
        Note:G-1
        >>> P5 - P4
        Interval:M2
        >>> M2 - P4
        Interval:m3
        >>> M2 - O
        Interval:m7
        """
        if not isinstance(other, Note):
            return self - Interval(steps=other)

        distance = self.scale_num - other.scale_num
        steps = self.steps - other.steps
        # Note     - Note     = Interval
        # Note     - Interval = Note
        # Interval - Note     = Interval  (doesn't make a huge amount of sense...)
        # Interval - Interval = Interval
        if not isinstance(self, Interval) and isinstance(other, Interval):
            accidental = steps - self._scale_num_to_steps(distance)
            return Note(scale_num=distance, accidental=accidental)
        else:
            distance = abs(distance)
            accidental = abs(steps) - self._scale_num_to_steps(distance)
            return Interval(distance=distance, accidental=accidental)

    def match(self, other, nooctave=True):
        if nooctave:
            return (self.steps - other.steps) % self._STEPS_PER_OCTAVE == 0
        else:
            return self.steps == other.steps

##################################################################

### Note Constants
#
# We provide a little more than an octave's worth of 
# 
#

C  = Note('C')
Cb = Note('Cb')
Cs = Note('C#')
Db = Note('Db')
D  = Note('D')
Ds = Note('D#')
Eb = Note('Eb')
E  = Note('E')
Es = Note('E#')
Fb = Note('Fb')
F  = Note('F')
Fs = Note('F#')
Gb = Note('Gb')
G  = Note('G')
Gs = Note('G#')
Ab = Note('Ab')
A  = Note('A')
As = Note('A#')
Bb = Note('Bb')
B  = Note('B')
Bs = Note('B#')
C1 = Note('C1')
D1 = Note('D1')
E1 = Note('E1')
F1 = Note('F1')

##################################################################

class Interval(Note):
    """
    Interval has the same attributes as Note: name, accidental, octave.  

    However, the name of the note doesn't really have much meaning
    when the Note is actually an Interval.  

    And when we say the "accidental" of an interval, we really mean
    whether it is major, minor, perfect, diminished, or augmented (or
    something else).  The accidental is stored as an integer, where 0
    means a perfect or major interval.

    We add a few properties, to indicate that Intervals give slightly
    different meaning to the attributes of the underlying Note object.

      distance      - this is the same as abs(scale_num) of the Note

                      For an Interval, the distance is the difference
                      between the scale_nums of two Notes.  So if the
                      notes are C and E, C is scale number 0, E is
                      scale number 2, so the distance is 2.

      interval_name - this is the name that we use when we talk about
                      the interval.  A distance of 2 is actually a
                      third.  This is just a string representation of
                      distance + 1.  

      interval_type - This is the string representation of the
                      accidental, where we translate

    """

    # --------------------------------------------------------- #
    # Interval: Class Attributes
    #

    _INTERVAL_NAMES=("UNISON",
                     "SECOND",
                     "THIRD",
                     "FOURTH",
                     "FIFTH",
                     "SIXTH",
                     "SEVENTH",
                     "OCTAVE",
                     "NINTH",
                     "TENTH",
                     "ELEVENTH",
                     "TWELFTH",
                     "THIRTEENTH",
                     "FOURTEENTH",
                     "FIFTEENTH")

    _PERFECT_INTERVAL_TYPES=("DIMINISHED",
                             "PERFECT",
                             "AUGMENTED")

    _INTERVAL_TYPES=("DIMINISHED",
                     "MINOR",
                     "MAJOR",
                     "AUGMENTED")

    # We map between types and their abbreviations using parallel
    # tuples.  This way the mapping is immutable.
    _ALL_TYPES   = ('DIMINISHED', 'MINOR', 'MAJOR', 'PERFECT', 'AUGMENTED')
    _TYPE_ABBREV = ('d',          'm',     'M',     'P',       'A')

    # --------------------------------------------------------- #
    # Interval: Class Methods
    #

    @classmethod
    def _interval_name_to_distance(cls, interval_name):
        interval_name = interval_name.upper()
        try:
            return cls._INTERVAL_NAMES.index(interval_name)
        except ValueError:
            match = re.match('^(%d)(ST|ND|RD|TH)$', interval_name)
            if match is not None:
                return match.group(0) - 1
            raise ValueError("Unknown interval " + interval_name)

    @classmethod
    def _distance_to_interval_name(cls, distance):
        distance = abs(distance)
        if distance < len(cls._INTERVAL_NAMES):
            return cls._INTERVAL_NAMES[distance]
        tens = int((distance % 100) / 10)
        ones = int(distance % 10)
        if tens == 2:
            sfx = "TH"
        elif ones == 1:
            sfx = "ST"
        elif ones == 2:
            sfx = "ND"
        elif ones == 3:
            sfx = "RD"
        else:
            sfx = "TH"
        return '%d%s' % (distance, sfx)

    @classmethod
    def _interval_type_to_accidental(cls, distance, interval_type):
        interval_type = interval_type.upper()
        distance = distance % cls._NOTES_PER_OCTAVE
        if (distance == 0 or
            distance == 3 or
            distance == 4):
            return cls._PERFECT_INTERVAL_TYPES.index(interval_type) - 1
        else:
            return cls._INTERVAL_TYPES.index(interval_type) - 2

    @classmethod
    def _accidental_to_interval_type(cls, distance, accidental):
        distance = distance % cls._NOTES_PER_OCTAVE
        if (distance == 0 or
            distance == 3 or
            distance == 4):
            if 0 <= (accidental + 1) < len(cls._PERFECT_INTERVAL_TYPES):
                return cls._PERFECT_INTERVAL_TYPES[accidental+1]
        else:
            if 0 <= (accidental + 2) < len(cls._INTERVAL_TYPES):
                return cls._INTERVAL_TYPES[accidental+2]
        if accidental > 0:
            return '+' + str(accidental)
        else:
            return str(accidental)

    @classmethod
    def _parse_short_name(cls, shorthand):
        match = re.match('^(\D)(\d+)$', shorthand)
        if match is None:
            raise ValueError("Can't parse " + shorthand)
        short_type = match.group(1)
        if short_type not in cls._TYPE_ABBREV:
            raise ValueError("Can't parse interval type %s from %s " % (short_type, shorthand))
        interval_type = cls._ALL_TYPES[cls._TYPE_ABBREV.index(short_type)]
        interval_num = int(match.group(2))
        if interval_num == 0:
            raise ValueError("Can't parse interval %d from %s " % (interval_num, shorthand))
        distance = abs(interval_num) - 1
        return (distance, interval_type)

    # --------------------------------------------------------- #
    # Interval: CTOR
    #

    def __init__(self, 
                 short=None,
                 interval_type=None, interval_name=None,
                 distance=None, 
                 accidental=None, 
                 steps=None, 
                 isotonic=None):

        if short is not None:
            if (interval_name is not None or
                distance is not None or
                steps is not None):
                raise ValueError("Cannot specify short with interval_name, distance, or steps")
            if isinstance(short, Note):
                super(Interval, self).__init__(short)
                return
            else:
                (distance, interval_type) = self._parse_short_name(short)

        if (interval_name is not None or distance is not None):
            # set distance
            if interval_name is not None:
                if isinstance(interval_name, basestring):
                    mydistance = self._interval_name_to_distance(interval_name)
                else:
                    mydistance = interval_name - 1
                if distance is not None and distance != mydistance:
                    raise ValueError("Interval %s does not match distance %d" % (interval_name, distance))
                distance = mydistance

            # set accidental
            if interval_type is not None:
                myaccidental = self._interval_type_to_accidental(distance, interval_type)
                if accidental is not None and accidental != myaccidental:
                    raise ValueError("Interval type %s does not match accidental %d" %
                                     (interval_type, accidental))
                accidental = myaccidental
            elif accidental is None:
                # or should we calculate the accidental from the steps?
                accidental = 0

            (name, octave) = self._scale_num_to_name(distance)
            super(Interval, self).__init__(name=name, accidental=accidental, 
                                           octave=octave, steps=steps,
                                           isotonic=isotonic)

        else:
            if (interval_type is not None or accidental is not None):
                raise ValueError("Must specify interval_name or distance when specifying interval_type or accidental")
            if steps is None:
                raise ValueError("Must specify interval_name, distance, or steps")
            super(Interval, self).__init__(steps=steps, isotonic=isotonic)

    # --------------------------------------------------------- #
    # Interval: Properties
    #

    @property
    def distance(self):
        return abs(self.scale_num)

    @property
    def interval_name(self):
        return self._distance_to_interval_name(self.distance)

    @property
    def interval_type(self):
        return self._accidental_to_interval_type(self.distance,
                                                 self.accidental)

    @property
    def interval_short_type(self):
        interval_type = self.interval_type
        if interval_type in self._ALL_TYPES:
            return self._TYPE_ABBREV[self._ALL_TYPES.index(interval_type)]
        return interval_type

    # --------------------------------------------------------- #
    # Interval: Methods
    #

    def __str__(self):
        return ("%s%d" % (self.interval_short_type, self.distance+1))

##################################################################

### Interval Constants

U   = Interval('P1')
d2  = Interval('d2')
m2  = Interval('m2')
M2  = Interval('M2')
A2  = Interval('A2')
d3  = Interval('d3')
m3  = Interval('m3')
M3  = Interval('M3')
A3  = Interval('A3')
d4  = Interval('d4')
P4  = Interval('P4')
A4  = Interval('A4')
d5  = Interval('d5')
P5  = Interval('P5')
A5  = Interval('A5')
d6  = Interval('d6')
m6  = Interval('m6')
M6  = Interval('M6')
A6  = Interval('A6')
d7  = Interval('d7')
m7  = Interval('m7')
M7  = Interval('M7')
A7  = Interval('A7')
O   = Interval('P8')

##################################################################

class Chord(FrozenClass):

    # --------------------------------------------------------- #
    # Chord: Class Attributes
    #

    _QUALITIES = {
        # triads
        'major':      (M3, P5),
        'minor':      (m3, P5),
        'augmented':  (M3, A5),
        'diminished': (m3, d5),

        # seventh chords
        'dominant-seventh':   (M3, P5, m7),
        'minor-seventh':      (m3, P5, m7),
        'major-seventh':      (M3, P5, M7),
        'augmented-seventh':  (M3, A5, m7),
        'diminished-seventh': (m3, d5, d7),
        'half-diminished-seventh': (m3, d5, m7)}

    _KEY_CHORDS = {'I'   : 1,
                   'II'  : 2,
                   'III' : 3,
                   'IV'  : 4,
                   'V'   : 5,
                   'VI'  : 6,
                   'VII' : 7}

    # --------------------------------------------------------- #
    # Chord: Class Methods
    #

    @staticmethod
    def _quality_is_seventh(quality):
        return quality.endswith('-seventh')

    @classmethod
    def _quality_to_intervals(cls, string):
        string=string.lower()
        if string in cls._QUALITIES:
            return cls._QUALITIES[string]
        if len(string) == 3:
            for quality in cls._QUALITIES:
                if quality.startswith(string):
                    return cls._QUALITIES[quality]
        elif len(string) == 4 and string[3] == '7':
            for quality in cls._QUALITIES:
                if (quality.startswith(string[0:2]) and
                    cls._quality_is_seventh(quality)):
                    return cls._QUALITIES[quality]
        return None

    @classmethod
    def _intervals_to_quality(cls, intervals):
        nintervals = len(intervals)
        if nintervals == 2 or nintervals == 3:
            for quality in cls._QUALITIES:
                if (nintervals == 2 and
                    len(cls._QUALITIES[quality]) == nintervals and
                    intervals[0] == cls._QUALITIES[quality][0] and
                    intervals[1] == cls._QUALITIES[quality][1]):
                    return quality
                if (nintervals == 3 and
                    len(cls._QUALITIES[quality]) == nintervals and
                    intervals[0] == cls._QUALITIES[quality][0] and
                    intervals[1] == cls._QUALITIES[quality][1] and
                    intervals[2] == cls._QUALITIES[quality][2]):
                    return quality
        return None

    @staticmethod
    def _notes_to_intervals(notes):
        return tuple(n - notes[0] for n in notes[1:])

    @classmethod
    def _notes_to_quality(cls, notes):
        return cls._intervals_to_quality(cls._notes_to_intervals(notes))

    @classmethod
    def _parse_short(cls, short, key):
        orig = short
        if short.endswith('7'):
            is_seventh = True
            short = short[:-1]
        else:
            is_seventh = False
        short_quality = short[-3:]
        try:
            root = Note(short=short[:-3])
            hasroot = True
        except:
            hasroot = False
        if hasroot:
            for quality in cls._QUALITIES:
                if (cls._quality_is_seventh(quality) == is_seventh and
                    short_quality == quality[:3]):
                    return (root, quality)
        if key is None:
            key = C
        if short.upper() in cls._KEY_CHORDS:
            scale_num = cls._KEY_CHORDS[short.upper()] - 1
            # By using the scale_num option of Notes, we are assuming
            # that the key is major.
            root = Note(scale_num=scale_num, accidental=None, octave=0)
            root = root + key
            if short == short.upper():
                quality = 'major'
            else:
                if short == 'vii':
                    # Special case: vii is diminished, not minor
                    quality = 'diminished'
                else:
                    quality = 'minor'
            return (root, quality)
        raise ValueError("Can't parse short name: %s" % orig)
            
    # --------------------------------------------------------- #
    # Chord: CTOR
    #

    def __init__(self, short=None, notes=None, key=None):
        super(Chord, self).__init__()
        if short is not None:
            if notes is not None:
                raise ValueError("Can't provide both short %s and notes %s" %
                                 (short, notes))
            (root, quality) = self._parse_short(short, key)
            intervals = self._quality_to_intervals(quality)
            self.notes = (root, ) + tuple(root + i for i in intervals)
        else:
            # make sure the notes are in order
            notelist = list(notes)
            notelist.sort()
            if len(notelist) == 0:
                raise ValueError("Chord must have at least one note")
            # add the key to the notes?
            self.notes = tuple(notelist)
        self.key = key
        self._freeze()

    # --------------------------------------------------------- #
    # Chord: Properties
    #

    @cached_attribute
    def root(self):
        if self.key is None:
            return self.notes[0]
        else:
            return self.notes[0] + self.key

    @cached_attribute
    def intervals(self):
        return self._notes_to_intervals(self.notes)

    @cached_attribute
    def quality(self):
        quality = self._notes_to_quality(self.notes)
        if quality is None:
            return "Unknown"
        else:
            return quality

    @cached_attribute
    def is_seventh_chord(self):
        return self._quality_is_seventh(self.quality)

    @cached_attribute
    def real_notes(self):
        if self.key is None:
            return self.notes
        else:
            return tuple((self.key + n) for n in self.notes)

    # --------------------------------------------------------- #
    # Chord: Methods
    #

    def __eq__(self, other):
        return (self.notes == other.notes and
                self.key == other.key)

    def __hash__(self):
        return hash((self.notes, self.key))

    def __str__(self):
        quality = self.quality
        if quality is None:
            return '[%s]' % '-'.join(self.notes)
        else:
            sfx = ''
            if self._quality_is_seventh(quality):
                sfx = '7'
            return "%s%s%s" % (self.root, self.quality[0:3], sfx)

    def __repr__(self):
        return "%s:%s" % (self.__class__.__name__, str(self))

    def __add__(self, other):
        if isinstance(other, Note):
            notes = ((n + other) for n in self.real_notes)
            return Chord(notes=notes)
        else:
            raise ValueError("Can only add notes and intervals to Chords")

    def has_note(self, note, exact=False):
        if exact:
            return note in self.real_notes
        else:
            return any(n.match(note) for n in self.real_notes)

    def match(self, other, nooctave=True):
        return all(s.match(o, nooctave=nooctave)
                   for (s, o) in
                   zip(self.real_notes, other.real_notes))

##################################################################

### Chord Constants

Cmaj = Chord(short='Cmaj')
Cmin = Chord(short='Cmin')
Cdim = Chord(short='Cdim')
Caug = Chord(short='Caug')
Dmaj = Chord(short='Dmaj')
Dmin = Chord(short='Dmin')
Ddim = Chord(short='Ddim')
Daug = Chord(short='Daug')
Emaj = Chord(short='Emaj')
Emin = Chord(short='Emin')
Edim = Chord(short='Edim')
Eaug = Chord(short='Eaug')
Fmaj = Chord(short='Fmaj')
Fmin = Chord(short='Fmin')
Fdim = Chord(short='Fdim')
Faug = Chord(short='Faug')
Gmaj = Chord(short='Gmaj')
Gmin = Chord(short='Gmin')
Gdim = Chord(short='Gdim')
Gaug = Chord(short='Gaug')
Amaj = Chord(short='Amaj')
Amin = Chord(short='Amin')
Adim = Chord(short='Adim')
Aaug = Chord(short='Aaug')
Bmaj = Chord(short='Bmaj')
Bmin = Chord(short='Bmin')
Bdim = Chord(short='Bdim')
Baug = Chord(short='Baug')

I   = Chord(notes=(C, E,  G))
ii  = Chord(notes=(D, F,  A))
iii = Chord(notes=(E, G,  B))
IV  = Chord(notes=(F, A,  C1))
V   = Chord(notes=(G, B,  D1))
vi  = Chord(notes=(A, C1, E1))
vii = Chord(notes=(B, D1, F1))  # diminished

PROGRESSIONS = ((I,   IV),  # Circle of fifths
                (IV,  vii),
                (vii, iii),
                (iii, vi),
                (vi,  ii),
                (ii,  V),
                (V,   I),

                (I,   V),   # Pachelbel
                (V,   vi),
                (vi,  iii),
                (iii, IV),
                (IV,  I),
                (IV,  V),
                
                (I,   vi),  # ii - IV - vi
                (vi,  IV),
                (IV,  vi),
                (IV,  ii),
                (ii,  IV),
                (ii,  vi),
                (vi,  ii),
                
                (IV,  I),   # other
                (I,   iii),
                (vi,  V),
                (V,   vi),
                (V,   ii))

CADENCES = ((V,  I), # Authentic
            (IV, I), # Plagal
            (I,  V), # Half
            (ii, V), # Half
            (IV, V), # Half
            (V, vi), # Deceptive
            (V, IV), # Deceptive
            (V, ii)) # Deceptive

FINAL_CADENCES = ((V,  I), # Authentic
                  (IV, I)) # Plagal

##################################################################

def apply_progression(progression, chord):
    if progression[1].intervals == chord.intervals:
        intv = chord.real_notes[0] - progression[1].real_notes[0]
        if chord.real_notes[0] < progression[1].real_notes[0]:
            intv = C - intv
        else:
            intv = Note(intv)
        return (progression[0] + intv, intv)
    else:
        return (None, None)

def get_harmonizations(harmonization, melody, progressions=None):
    harmonizations = []
    step = len(melody) - len(harmonization)
    melody_note = melody[step-1]
    prev_chord = harmonization[0]
    if progressions is None:
        if len(harmonization) == 1:
            progressions = CADENCES
        else:
            progressions = PROGRESSIONS
    seen = []
    for progression in progressions:
        (chord, key) = apply_progression(progression, prev_chord)
        if (chord is not None and
            chord.has_note(melody_note) and
            not any(c.match(chord) for c in seen)):
            new_harm = [chord]
            new_harm.extend(harmonization)
            harmonizations.append(new_harm)
            seen.append(chord)
            debug("{0}->{1} is {2} in {3} Major".format(chord, prev_chord,
                                                        progression, key))
    return harmonizations

def fill_harmonizations(harmonizations, melody):
    new_harm = []
    for h in harmonizations:
        new_harm.extend(get_harmonizations(h, melody))
    return new_harm

def harmonize(melody=(C, D, E, D, C), final_chord=None):
    if final_chord is None:
        final_chord = Cmaj + melody[-1]
    harmonizations = [[final_chord]]
    for i in range(len(melody)-1):
        harmonizations = fill_harmonizations(harmonizations, melody)
    return harmonizations

##################################################################

#
# Given 
#   a string of notes (represented as A-G)
#   a list of allowed chord progressions (represented as I->IV, aka "chord-in-key")
#   a list of allowed chord progressions at the end of the piece
#   the final chord (the actual notes, not a chord-in-key)
#
# return one (or all?) possible harmonizations
#   just chords, or the actual notes (if the latter, need to do voice leading: also check for parallel fifths/octaves, augmented 2nds)
#   for each chord, which progression it's part of
#
# Start from the end.  We are given the final chord (and key).  
# Convert the chord into the chord-in-key
# find all possible previous chords-in-key
# convert those into chords
# repeat
#
# function: 
#   given a chord and a key, find the chord-in-key
#   given a chord, find all possible chords-in-key
#   given a sequence of chords-in-key, find all progressions ending in the beginning of the sequence
#   find the chord-in-keys that match the next note
#   given a chord-in-key, and a key, find the chord.  
#
#  - class Key
#    - represented as list of notes in the scale
#    - methods:
#      - can get nth note of scale
#      - list accidentals (in order)
#      - can name the scale, deduce the scale from a name
#      - return a chord-in-key built on the Nth note of the key
#  - class Chord
#    - has
#      - a key
#      - a list of the notes, including the root, as if the Key were C
#        - when calculating the actual notes, add the key to each note
#        - a list of notes or a list of intervals?
#          - if a list of intervals, it would be intervals from the root of the Key, as if the Key started at C
#            i.e., F-A-C1 == P4-M6-P8, not P4 + M3 + m3
#    - represent
#      - a chord with all specific tones ("F major")
#        - represented as F-A-C1 with no key
#      - a chord that is built on the Nth note of a Key, where the Key is not specified ("IV")
#        - represented as F-A-C1 with no key
#      - a chord that is built on the Nth note of a Key, where the Key is specified ("IV of D" == "G major")
#        - represented as F-A-C1 with Key = D0
#      - a generic chord type, like "Major" or "Minor" (do we need this?)
#        - represented as C-E-G with no key
#    - methods
#      - a function/property that deduces the type of the chord based on
#        the notes
#      - a function that deduces the notes from a string and vice versa:
#          http://en.wikipedia.org/wiki/Interval_(music)#Intervals_in_chords
#      - two chords are equal if the root notes are equal and the
#        component notes are equal w/o octave in any order
#        - hash like this too.  
#      - function: is a given note part of a given chord?
#      - function: given a note and a chord w/o a root, return chords
#        that contain the given note, and the key that the chord would be
#        part of
#      - compare two chords to see if they have the same type
#    - freeze the class after init
#
#

##################################################################

#
# To profile, run:
#    python -m cProfile -o output.txt code/github/Harmonize/harmonize.py D A B A G 'F#' E D
# Then, in ipython:
#    import pstats
#    p = pstats.Stats('output.txt')
#    psort_stats('cumulative').print_stats(10)
#
def main():
    """
    Main body of the script.
    """
    opts,args = getopts()
    if opts.doctest:
        import doctest
        doctest.testmod(verbose=opts.verbose)
        return

    if opts.verbose:
        logat('DEBUG')
    if len(args) > 0:
        h = harmonize(melody=tuple(Note(a) for a in args))
    else:
        h = harmonize()
    for harmony in h:
        print harmony

def getopts():
    """
    Parse the command-line options
    """
    parser = OptionParser()
    parser.add_option('--doctest', '--test',
                      action='store_true',
                      help='run the doctest')
    parser.add_option('--verbose', '-v',
                      action='store_true',
                      help='verbose')
    opts,args = parser.parse_args()
    return (opts,args)

##################################################################

if __name__ == "__main__":
    main()
