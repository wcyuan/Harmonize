#!/usr/local/bin/python
"""
harmonize.py [<options>] [...args...]

Description: Module for music notation

Created by: Conan Yuan (yuanc), 20111218

"""
#
# 

from __future__ import division, absolute_import, with_statement
from logging    import debug, getLogger, getLevelName
from optparse   import OptionParser
from math       import floor
import re

__version__ = "$Revision: 1.12 $"

##################################################################

def logat(level=None):
    if level is None:
        return getLevelName(getLogger(__name__).level)
    else:
        getLogger(__name__).setLevel(level)

##################################################################

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
           'O'
           ]

##################################################################

class FrozenClass(object):
    __is_frozen = False
    def __setattr__(self, key, value):
        if self.__is_frozen:
            raise TypeError( "%r is a frozen class" % self )
        object.__setattr__(self, key, value)

    def _freeze(self):
        self.__is_frozen = True

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

    """

    # --------------------------------------------------------- #
    # Class Attributes
    #

    __is_frozen = False

    _NOTE_ORDER = ('C', 'D', 'E', 'F', 'G', 'A', 'B')
    _STEPS_PER_OCTAVE = 12
    _NOTES_PER_OCTAVE = len(_NOTE_ORDER)
    _ACCIDENTAL_SYMS = ('bb', 'b', '', '#', 'x')

    isotonic_is_equal = True

    # --------------------------------------------------------- #
    # Class Methods
    #

    @classmethod
    def _steps_to_scale_num(cls, steps, flat=False):
        """
        >>> from my.harmonize import *
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
        octave = int(floor(steps / cls._STEPS_PER_OCTAVE))
        adj_steps = steps % cls._STEPS_PER_OCTAVE
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
        #debug("steps %d -> adj_steps %d, scale_num %d, accidental %d" % (steps, adj_steps, scale_num, accidental))
        return (scale_num, accidental, octave)

    @classmethod
    def _scale_num_to_steps(cls, scale_num, accidental=0, octave=0):
        """
        >>> from my.harmonize import *
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
        if scale_num % cls._NOTES_PER_OCTAVE > 2:
            steps -= 1
        steps += octave * cls._STEPS_PER_OCTAVE
        steps += accidental
        return steps

    @classmethod
    def _scale_num_to_name(cls, scale_num):
        """
        >>> from my.harmonize import *
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
        >>> from my.harmonize import *
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
        >>> from my.harmonize import *
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
        steps += octave * 12
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
        >>> from my.harmonize import *
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
            ValueError("Can't parse " + shorthand)

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
    # CTOR
    #

    def __init__(self, 
                 short=None,
                 name=None, accidental=None, octave=None, 
                 scale_num=None, 
                 steps=None, 
                 flat=False, sharp=False, 
                 isotonic=None):

        if short is not None:
            if (name is not None or
                scale_num is not None or
                steps is not None):
                ValueError("Cannot specify short with name, scale_num, or steps")
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
                    ValueError("Name %s doesn't match scale num %d" % (name, scale_num))
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
                ValueError("Name %s has steps %d not %d" %
                           (self._str_name(name, accidental, octave),
                            self.steps, steps))
        else:
            if steps is None:
                ValueError("Must specify note name or steps")
            if (accidental is not None or octave is not None):
                ValueError("Cannot specify accidental or octave without specifying the note name")
            (scale_num, myaccidental, myoctave) = self._steps_to_scale_num(steps)
            self.name = self._scale_num_to_name(scale_num)[0]
            self.accidental = myaccidental
            self.octave = myoctave

        if isotonic is not None:
            self.isotonic_is_equal = isotonic

        self._freeze()

    # --------------------------------------------------------- #
    # Properties
    #

    @property
    def scale_num(self):
        return self._scale_name_to_num(self.name, self.octave)

    @property
    def steps(self):
        return self._name_to_steps(self.name, self.accidental, self.octave)

    # --------------------------------------------------------- #
    # Methods
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

        >>> from my.harmonize import *
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

        >>> from my.harmonize import *
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
        >>> P5 - P4
        Interval:M2
        >>> M2 - P4
        Interval:m3
        >>> M2 - O
        Interval:m7
        """
        if not isinstance(other, Note):
            return self - Interval(steps=other)

        distance = abs(self.scale_num - other.scale_num)
        accidental = abs(self.steps - other.steps) - self._scale_num_to_steps(distance)

        # Note     - Note     = Interval
        # Note     - Interval = Note
        # Interval - Note     = Interval  (doesn't make a huge amount of sense...)
        # Interval - Interval = Interval
        if not isinstance(self, Interval) and isinstance(other, Interval):
            return Note(scale_num=distance, accidental=accidental)
        else:
            return Interval(distance=distance, accidental=accidental)

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
    # Class Attributes
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
    # Class Methods
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
            ValueError("Unknown interval " + interval_name)

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
            ValueError("Can't parse " + shorthand)
        short_type = match.group(1)
        if short_type not in cls._TYPE_ABBREV:
            ValueError("Can't parse interval type %s from %s " % (short_type, shorthand))
        interval_type = cls._ALL_TYPES[cls._TYPE_ABBREV.index(short_type)]
        interval_num = int(match.group(2))
        if interval_num == 0:
            ValueError("Can't parse interval %d from %s " % (interval_num, shorthand))
        distance = abs(interval_num) - 1
        return (distance, interval_type)

    # --------------------------------------------------------- #
    # CTOR
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
                ValueError("Cannot specify short with interval_name, distance, or steps")
            (distance, interval_type) = self._parse_short_name(short)

        if (interval_name is not None or distance is not None):
            # set distance
            if interval_name is not None:
                if isinstance(interval_name, basestring):
                    mydistance = self._interval_name_to_distance(interval_name)
                else:
                    mydistance = interval_name - 1
                if distance is not None and distance != mydistance:
                    ValueError("Interval %s does not match distance %d" % (interval_name, distance))
                distance = mydistance

            # set accidental
            if interval_type is not None:
                myaccidental = self._interval_type_to_accidental(distance, interval_type)
                if accidental is not None and accidental != myaccidental:
                    ValueError("Interval type %s does not match accidental %d" %
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
                ValueError("Must specify interval_name or distance when specifying interval_type or accidental")
            if steps is None:
                ValueError("Must specify interval_name, distance, or steps")
            super(Interval, self).__init__(steps=steps, isotonic=isotonic)

    # --------------------------------------------------------- #
    # Properties
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
    # Methods
    #

    def __str__(self):
        return ("%s%d" % (self.interval_short_type, self.distance+1))

##################################################################

class Chord(FrozenClass):
    _notes = None
    
    pass

##################################################################
# constants

### Notes

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

### Intervals

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
#

##################################################################

def main():
    """
    Main body of the script.
    """
    opts,args = getopts()
    import doctest
    doctest.testmod()

def getopts():
    """
    Parse the command-line options
    """
    parser = OptionParser()
    opts,args = parser.parse_args()
    return (opts,args)

##################################################################

if __name__ == "__main__":
    main()
