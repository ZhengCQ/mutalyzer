#!/usr/bin/python

"""
    The nomenclature checker.
"""

import sys
import math
import types
import Bio

import Bio.Seq
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.SeqUtils import seq3

from Modules import Retriever
from Modules import GenRecord
from Modules import Crossmap
from Modules import Parser
from Modules import Db
from Modules import Mutator
from Modules import Output
from Modules import Config

#def __order(a, b) :
#    """
#    """
#
#    if a < b :
#        return a, b
#    return b, a
##__order

def __roll(ref, start, stop) :
    """
    """

    pattern = ref[start - 1:stop]
    patternLength = len(pattern)

    minimum = start - 2
    j = patternLength - 1
    while minimum > -1 and ref[minimum] == pattern[j % patternLength] :
        j -= 1
        minimum -= 1
    #while 

    maximum = stop
    j = 0
    while maximum < len(ref) and ref[maximum] == pattern[j % patternLength] :
        j += 1
        maximum += 1
    #while 

    return start - minimum - 2, maximum - stop
#__roll

def __palinsnoop(string) :
    """
    """

    revcomp = Bio.Seq.reverse_complement(string)

    for i in range(int(math.ceil(len(string) / 2.0))) :
        if string[i] != revcomp[i] :
            return i # The first i elements are palindromic.
    return -1        # Perfect palindrome.
#__palinsnoop

def __bprint(s) :
    """
    """

    if not s :
        return

    block = 10
    line = 6 * block

    m = int(math.floor(math.log(len(s), 10)) + 1)
    o = 1
    print "%s " % str(o).rjust(m),
    for i in range(0, len(s), block) :
        print s[i:i + block],
        if not (i + block) % line and i + block < len(s) :
            o += line
            print "\n%s " % str(o).rjust(m),
        #if
    #for
#__bprint

def __PtLoc2main(Loc) :
    """
    """

    main = int(Loc.Main)
    if Loc.MainSgn == '-' :
        main = -main

    return main
#__PtLoc2main

def __PtLoc2offset(Loc) :
    """
    """

    if Loc.Offset :
        offset = int(Loc.Offset)
        if Loc.OffSgn == '-' :
            offset = -offset
    #if
    else :
        offset = 0

    return offset
#__PtLoc2offset

def __splice(string, splice_sites) :
    """
        Construct the transcript or the coding sequence from a record and
        a list of splice sites.

        Arguments:
            record       ; A GenBank record (see the BioPython documentation).
            splice_sites ; A list of even length of integers.

        Returns:
            String ; The concatenation of slices from the sequence that is 
                     present in the GenBank record.
    """

    transcript = ""

    for i in range(0, len(splice_sites), 2) :
        transcript += string[splice_sites[i] - 1:splice_sites[i + 1]] 

    return transcript
#__splice

def __nsplice(string, splice_sites, CDS, orientation) :
    """
    """

    transcript = ""

    if orientation == 1 :
        for i in range(0, len(splice_sites), 2) :
            if CDS[0] >= splice_sites[i] and CDS[0] <= splice_sites[i + 1] :
                transcript += string[CDS[0] - 1:splice_sites[i + 1]]
            else :
                if splice_sites[i] > CDS[0] :
                    transcript += \
                        string[splice_sites[i] - 1:splice_sites[i + 1]] 
        #for
    #if        
    else :
        for i in range(0, len(splice_sites), 2) :
            if CDS[1] >= splice_sites[i] and CDS[1] <= splice_sites[i + 1] :
                transcript += string[splice_sites[i] - 1: CDS[1]]
            else :
                if splice_sites[i] < CDS[1] :
                    transcript += \
                     string[splice_sites[i] - 1:splice_sites[i + 1]] 
        #for
    #else        

    return transcript
#__nsplice

def __checkOptArg(ref, p1, p2, arg, O) :
    """
    """

    if arg :
        if arg.isdigit() :
            length = int(arg)
            interval = p2 - p1 + 1
            if length != interval :
                O.addMessage(__file__, 3, "EARGLEN", 
                    "The length (%i) differed from that of the range (%i)." % (
                    length, interval))
                return False
            #if
        #if
        else :
            ref_slice = str(ref[p1 - 1:p2])
            if ref_slice != str(arg) : # FIXME more informative.
                O.addMessage(__file__, 3, "EREF", 
                    "%s not found at position %i_%i, found %s instead." % (
                    arg, p1, p2, ref_slice))
                return False
            #if
        #else
    #if
    return True
#__checkOptArg

def __lcp(str1, str2) :
    """
        Calculate the length of the longest common prefix of two strings.

        Arguments:
            str1 ; The first string.
            str2 ; The second string.

        Returns:
            integer ; The length of the longest common prefix of str1 and str2.
    """

    pos = 0
    s1l = len(str1) # Use the lengths to make sure we don't exceed the length
    s2l = len(str2) # of the strings.

    while pos < s1l and pos < s2l and str1[pos] == str2[pos] :
        pos += 1

    return pos
#__lcp

def __lcs(str1, str2) :
    """
        Calculate the length of the longest common suffix of two strings.

        Arguments:
            str1 ; The first string.
            str2 ; The second string.

        Returns:
            integer ; The length of the longest common suffix of str1 and str2.
    """

    t1 = str1[::-1] # Invert str1.
    t2 = str2[::-1] # Invert str2.

    # The lcp of the two inverted strings is the lcs of the original strings.
    return __lcp(t1, t2) 
#__lcs

def findInFrameDescription(str1, str2) :
    """
    """

    # Nothing happened.
    if str1 == str2 :
        return "p.(=)"

    lcp = __lcp(str1, str2)
    lcs = __lcs(str1[lcp:], str2[lcp:])
    str1_end = len(str1) - lcs
    str2_end = len(str2) - lcs

    # Insertion / Duplication.
    if not str1_end - lcp :
        inLen = str2_end - lcp

        if lcp - inLen >= 0 and str1[lcp - inLen:lcp] == str2[lcp:str2_end] :
            if inLen == 1 :
                return "p.(%s%idup)" % (seq3(str1[lcp - inLen]), 
                                        lcp - inLen + 1)
            return "p.(%s%i_%s%idup)" % (seq3(str1[lcp - inLen]), 
                                         lcp - inLen + 1,
                                         seq3(str1[lcp - 1], lcp))
        #if
        return "p.(%s%i_%s%iins%s)" % (seq3(str1[lcp - 1]), lcp, 
                                       seq3(str1[lcp]), lcp + 1,
                                       seq3(str2[lcp:str2_end]))
    #if

    # Deletion.
    if not str2_end - lcp :
        if lcp + 1 == str1_end :
            return "p.(%s%idel)" % (seq3(str1[lcp]), lcp + 1)
        return "p.(%s%i_%s%idel)" % (seq3(str1[lcp - 1]), lcp + 1, 
                                     seq3(str1[str1_end - 1]), str1_end)
    #if

    # Substitution.
    if str1_end == str2_end and str1_end == lcp + 1 :
        if len(str1) > len(str2) :
            return "p.(*%i%sext*%i)" % (len(str1) + 1, seq3(str2[len(str1)]), 
                                        abs(len(str1) - len(str2)))
        if len(str1) > len(str2) :
            return "p.(%s%i*)" % (seq3(str1[len(str2)]), len(str2) + 1)
        return "p.(%s%i%s)" % (seq3(str1[lcp]), lcp + 1, seq3(str2[lcp]))
    #if

    # InDel.
    if lcp + 1 == str1_end :
        return "p.(%s%idelins%s)" % (seq3(str1[lcp]), lcp + 1, 
                                     seq3(str2[lcp:str2_end]))
    return "p.(%s%i_%s%idelins%s)" % (seq3(str1[lcp]), lcp + 1, 
                                      seq3(str1[str1_end - 1]),
                                      str1_end, seq3(str2[lcp:str2_end]))
#findInFrameDescription

def findFrameShift(str1, str2) :
    """
    """

    lcp = __lcp(str1, str2)

    return "p.(%s%i%sfs*%i)" % (seq3(str1[lcp]), lcp + 1, seq3(str2[lcp]),
                                len(str2) - lcp)
#findFrameShift

def __toProtDescr(CDSStop, orig, trans) :
    """
    """

    if CDSStop % 3 :
        return findFrameShift(str(orig), str(trans))
    return findInFrameDescription(str(orig), str(trans))
#__toProtDescr

#def __trim(string, lcp, lcs) :
#    """
#    """
#
#    return string[lcp:len(string) - lcs]
##__trim

def __trim2(str1, str2) :
    """
    """

    lcp = __lcp(str1, str2)
    lcs = __lcs(str1[lcp:], str2[lcp:])
    return str1[lcp:len(str1) - lcs], str2[lcp:len(str2) - lcs], lcp, lcs
#__trim2

def __rangeToC(M, g1, g2) :
    """
    """

    if M.orientation == -1 :
        return M.g2c(g2), M.g2c(g1)
    return M.g2c(g1), M.g2c(g2)
#__rangeToC

def checkSubstitution(start_g, Arg1, Arg2, MUU, GenRecordInstance, record, O) :
    """
    """

    if Arg1 == Arg2 :
        O.addMessage(__file__, 3, "ENOVAR", 
            "No mutation given (%c>%c) at position %i." % (
            Arg1, Arg1, start_g))
    MUU.subM(start_g, Arg2)
    GenRecordInstance.name(start_g, start_g, "subst", record.seq[start_g - 1], 
                           Arg2, None)
#checkSubstitution
    
def checkDeletionDuplication(start_g, end_g, mutationType, MUU, 
                             GenRecordInstance, record, O) :
    """
    """

    roll = __roll(record.seq, start_g, end_g)
    if roll[1] :
        newStart = start_g + roll[1]
        newStop = end_g + roll[1]
        O.addMessage(__file__, 2, "WROLL", 
            "Sequence %s at position %i_%i was given, however, " \
            "the HGVS notation prescribes that it should be %s at " \
            "position %i_%i." % (str(record.seq[start_g - 1:end_g]), 
            start_g, end_g, str(record.seq[newStart - 1:newStop]), 
            newStart, newStop))
    #if
    if mutationType == "del" :
        MUU.delM(start_g, end_g)
    else :
        MUU.dupM(start_g, end_g)
    GenRecordInstance.name(start_g, end_g, mutationType, "", "", 
                           roll)
#checkDeletionDuplication
    
def checkInversion(start_g, end_g, MUU, GenRecordInstance, record, O) :
    """
    """

    snoop = __palinsnoop(record.seq[start_g - 1:end_g])
    if snoop :
        if snoop == -1 :
            O.addMessage(__file__, 2, "WNOCHANGE", 
                "Sequence %s at position %i_%i is a palindrome " \
                "(its own reverse complement)." % (
                str(record.seq[start_g - 1:end_g]), start_g, end_g))
            return
        #if
        else :
            O.addMessage(__file__, 2, "WNOTMINIMAL", 
                "Sequence %s at position %i_%i is a partial " \
                "palindrome (the first %i nucleotide(s) are the reverse " \
                "complement of the last one(s)), the HGVS notation " \
                "prescribes that it should be %s at position %i_%i." % (
                str(record.seq[start_g - 1:end_g]), 
                start_g, end_g, snoop, 
                str(record.seq[start_g + snoop - 1: end_g - snoop]),
                start_g + snoop, end_g - snoop))
            start_g += snoop
            end_g -= snoop
        #else
    #if
    # FIXME if length == 1 -> substitution.
    MUU.invM(start_g, end_g)
    GenRecordInstance.name(start_g, end_g, "inv", "", "", None)
#checkInversion
    
def checkInsertion(start_g, end_g, Arg1, MUU, GenRecordInstance, record, O) :
    """
    """

    if start_g + 1 != end_g :
        O.addMessage(__file__, 3, "EINSRANGE", 
            "%i and %i are not consecutive positions." % (start_g, end_g))
    MUU.insM(start_g, Arg1)
    insertionLength = len(Arg1)
    newStart = MUU.shiftpos(start_g)
    newStop = MUU.shiftpos(start_g) + insertionLength
    roll = __roll(MUU.mutated, newStart + 1, newStop)
    if roll[0] + roll[1] >= insertionLength :
        O.addMessage(__file__, 2, "WINSDUP", 
            "Insertion of %s at position %i_%i was given, " \
            "however, the HGVS notation prescribes that it should be a " \
            "duplication of %s at position %i_%i." % (
            MUU.mutated[newStart:newStop], start_g, start_g + 1,
            MUU.mutated[newStart:newStop], start_g + roll[1], 
            start_g + roll[1] + insertionLength - 1))
        end_g += roll[1] - 1
        start_g = end_g - insertionLength + 1
        GenRecordInstance.name(start_g, end_g, "dup", "", "", 
                               (roll[0] + roll[1] - insertionLength, 0))
    #if
    else :
        GenRecordInstance.name(start_g, start_g + 1, "ins", 
            MUU.mutated[newStart + roll[1]:newStop + roll[1]] , "", 
            roll)
#checkInsertion

def __rv(MUU, record, RawVar, GenRecordInstance, parts, O, transcript) :
    """
    """

    # First assume that the variant is given in g. notation.
    start_g = int(RawVar.StartLoc.PtLoc.MainSgn + RawVar.StartLoc.PtLoc.Main)
    start_offset = __PtLoc2offset(RawVar.StartLoc.PtLoc)
    end_g = start_g
    end_offset = start_offset
    if RawVar.EndLoc :
        end_g = int(RawVar.EndLoc.PtLoc.MainSgn + RawVar.EndLoc.PtLoc.Main)
        end_offset = __PtLoc2offset(RawVar.EndLoc.PtLoc)
    #if
    Arg1 = RawVar.Arg1
    Arg2 = RawVar.Arg2

    
    # If it is not, convert it to g. notation.
    if transcript :
        start_g = transcript.CM.x2g(start_g, start_offset)
        end_g = transcript.CM.x2g(end_g, end_offset)
        if transcript.CM.orientation == -1 :
            Arg1 = Bio.Seq.reverse_complement(RawVar.Arg1)
            Arg2 = Bio.Seq.reverse_complement(RawVar.Arg2)
            start_g, end_g = end_g, start_g
        #if
    #if

    if RawVar.MutationType in ["del", "dup", "subst", "delins"] :
        __checkOptArg(record.seq, start_g, end_g, Arg1, O)

    if RawVar.MutationType == "subst" :
        checkSubstitution(start_g, Arg1, Arg2, MUU, GenRecordInstance, record, 
                          O)
    if RawVar.MutationType in ["del", "dup"] :
        checkDeletionDuplication(start_g, end_g, RawVar.MutationType, MUU, 
                                 GenRecordInstance, record, O)
    if RawVar.MutationType == "inv" :
        checkInversion(start_g, end_g, MUU, GenRecordInstance, record, O)
    if RawVar.MutationType == "ins" :
        checkInsertion(start_g, end_g, Arg1, MUU, GenRecordInstance, record, O)


    # DelIns.
    if RawVar.MutationType == "delins" :
        if not Arg1 :
            Arg1 = MUU.orig[start_g - 1:end_g]

        #lcp =  __lcp(Arg1, Arg2)
        #lcs =  __lcs(Arg1, Arg2)

        if str(Arg1) == str(Arg2) :
            O.addMessage(__file__, 2, "WNOCHANGE", 
                "Sequence %s at position %i_%i is identical to the " \
                "variant." % (
                str(record.seq[start_g - 1:end_g]), 
                start_g, end_g))
            return
        #if
        #ins_part = Arg2

        #del_part = __trim(Arg1, lcp, lcs)
        #ins_part = __trim(Arg2, lcp, lcs)
        del_part, ins_part, lcp, lcs = __trim2(Arg1, Arg2)
        if not len(del_part) :
            O.addMessage(__file__, 2, "WWRONGTYPE", "The given DelIns " \
                         "is actually an insertion.")
            checkInsertion(start_g + lcp - 1, start_g + lcp, ins_part, MUU,
                           GenRecordInstance, record, O)
            return                               
        #if                
        if len(del_part) == 1 and len(ins_part) == 1 :
            O.addMessage(__file__, 2, "WWRONGTYPE", "The given DelIns " \
                         "is actually a substitution.")
            checkSubstitution(start_g + lcp, del_part, ins_part, MUU, 
                              GenRecordInstance, record, O)
            return                                  
        #if                
        if not len(ins_part) :
            O.addMessage(__file__, 2, "WWRONGTYPE", "The given DelIns " \
                         "is actually a deletion.")
            checkDeletionDuplication(start_g + lcp, end_g - lcs, "del", 
                                     MUU, GenRecordInstance, record, O)
            return                                  
        #if                
        if str(Bio.Seq.reverse_complement(del_part)) == ins_part :
            O.addMessage(__file__, 2, "WWRONGTYPE", "The given DelIns " \
                         "is actually an inversion.")
            checkInversion(start_g + lcp, end_g - lcs, MUU,
                           GenRecordInstance, record, O)
            return                                  
        #if                

        MUU.delinsM(start_g + lcp, end_g - lcs, ins_part)

        GenRecordInstance.name(start_g, end_g, "delins", ins_part, "", None)
    #if
#__rv

def __ppp(MUU, record, parts, GenRecordInstance, O) :
    if parts.RawVar or parts.SingleAlleleVarSet :
        if parts.RefType in ['c', 'n'] :
            if parts.Gene :
                if parts.Gene.GeneSymbol :
                    GS = GenRecordInstance.record.findGene(
                         parts.Gene.GeneSymbol)
                else :
                    GS = GenRecordInstance.record.geneList[0]
                if parts.Gene.TransVar :
                    W = GS.findLocus(parts.Gene.TransVar)
                else :
                    W = GS.transcriptList[0]
            #if
            else :
                W = GenRecordInstance.record.geneList[0].transcriptList[0]
        #if
        else :
            W = None

        if parts.SingleAlleleVarSet :
            for i in parts.SingleAlleleVarSet :
                __rv(MUU, record, i.RawVar, GenRecordInstance, 
                     parts, O, W)
        #if
        else :
            __rv(MUU, record, parts.RawVar, GenRecordInstance, parts, O, W)


        if not W : # Genomic given.
            return
        if not GenRecordInstance.record.geneList : # EST
            return

        cds = Seq(str(__splice(MUU.orig, W.CDS.positionList)), 
                  IUPAC.unambiguous_dna)
        cdsm = Seq(str(__nsplice(MUU.mutated, 
                                 MUU.newSplice(W.mRNA.positionList), 
                                 MUU.newSplice(W.CDS.location), 
                                 W.CM.orientation)),
                   IUPAC.unambiguous_dna)
        if W.CM.orientation == -1 :
            cds = Bio.Seq.reverse_complement(cds)
            cdsm = Bio.Seq.reverse_complement(cdsm)
        #if

        if '*' in cds.translate()[:-1] :
            O.addMessage(__file__, 3, "ESTOP", "In frame stop codon found.")
            return
        #if
        orig = cds.translate(table = W.txTable, cds = True, to_stop = True)
        O.addOutput("oldprotein", orig + '*')
        trans = cdsm.translate(table = W.txTable, to_stop = True)

        if not trans or trans[0] != 'M' :
            if str(cdsm[0:3]) in \
                Bio.Data.CodonTable.unambiguous_dna_by_id[
                    W.txTable].start_codons :
                O.addOutput("newprotein", '?')
                O.addOutput("altstart", str(cdsm[0:3]))
                O.addOutput("altprotein", 'M' + trans[1:] + '*')
            else :
                O.addOutput("newprotein", '?')
        else :
            O.addOutput("newprotein", trans + '*')

        #if not parts.SingleAlleleVarSet :
        #    #O.addOutput("proteindescription", "p.?")
        #    # FIXME
        #    O.addOutput("proteindescription", __toProtDescr(
        #        W.CM.g2x(MUU.newSplice(W.CDS.location)[1])[0], orig, trans))
        #else :
        #    O.addOutput("proteindescription", "p.?")
            
        #del W.CM
    #if                
#__ppp

def process(cmd, C, O) :
    parser = Parser.Nomenclatureparser(O)
    O.addOutput("inputvariant", cmd)
    ParseObj = parser.parse(cmd)
    del parser

    if ParseObj :
        if ParseObj.Version :
            RetrieveRecord = ParseObj.RefSeqAcc + '.' + ParseObj.Version
        else :
            RetrieveRecord = ParseObj.RefSeqAcc
        O.addOutput("reference", RetrieveRecord)
        
        D = Db.Cache(C.Db)
        retriever = Retriever.Retriever(C.Retriever, O, D)
        record = retriever.loadrecord(RetrieveRecord)
        if not record :
            return
        del retriever
        del D
        
        GenRecordInstance = GenRecord.GenRecord(C.GenRecord, O)
        GenRecordInstance.parseRecord(record)
        GenRecordInstance.checkRecord()

        MUU = Mutator.Mutator(record.seq, C.Mutator, O)
        __ppp(MUU, record, ParseObj, GenRecordInstance, O)

        # PROTEIN
        for i in GenRecordInstance.record.geneList :
            for j in i.transcriptList :
                if not ';' in j.description and j.CDS :
                    cds = Seq(str(__splice(MUU.orig, j.CDS.positionList)), 
                              IUPAC.unambiguous_dna)
                    cdsm = Seq(str(__nsplice(MUU.mutated, 
                                             MUU.newSplice(j.mRNA.positionList), 
                                             MUU.newSplice(j.CDS.location), 
                                             j.CM.orientation)),
                               IUPAC.unambiguous_dna)
                    cdsStop = 1                               
                    if j.CM.orientation == -1 :
                        cds = Bio.Seq.reverse_complement(cds)
                        cdsm = Bio.Seq.reverse_complement(cdsm)
                        cdsStop = 0
                    #if

                    #if '*' in cds.translate()[:-1] :
                    #    O.addMessage(__file__, 3, "ESTOP", 
                    #                 "In frame stop codon found.")
                    #    return
                    ##if
                    orig = cds.translate(table = j.txTable, cds = True, 
                                         to_stop = True)
                    #O.addOutput("oldprotein", orig + '*')
                    trans = cdsm.translate(table = j.txTable, to_stop = True)

                    #print i.name, j.name
                    #print j.CDS.location
                    j.proteinDescription = __toProtDescr(
                        j.CM.g2x(MUU.newSplice(j.CDS.location)[cdsStop])[0], 
                                 orig, trans)
                    #print j.proteinDescription                                 

        # /PROTEIN

        del MUU
        return GenRecordInstance
    #if
#process

def main(cmd) :
    C = Config.Config()
    O = Output.Output(__file__, C.Output)

    O.addMessage(__file__, -1, "INFO", "Received variant " + cmd)

    RD = process(cmd, C, O)

    O.addMessage(__file__, -1, "INFO", "Finished processing variant " + cmd)

    ### OUTPUT BLOCK ###
    gn = O.getOutput("genename")
    if gn :
        print "Gene Name: " + gn[0]
    tv = O.getOutput("transcriptvariant")
    if tv :
        print "Transcript variant: " + tv[0]
        print
    #if
    
    O.getMessages()
    errors, warnings, summary = O.Summary()
    print summary
    print

    #if not errors :
    if not False :
        visualisation = O.getOutput("visualisation")
        if visualisation :
            for i in range(len(visualisation)) :
                if i and not i % 3 :
                    print
                print visualisation[i]
            #for
            print
        #if

        reference = O.getOutput("reference")[0]

        for i in RD.record.geneList :
            for j in i.transcriptList :
                if ';' in j.description :
                    print "%s(%s_v%s):%c.[%s]" % (reference, i.name, j.name, 
                                                  j.molType, j.description)
                else :
                    print "%s(%s_v%s):%c.%s" % (reference, i.name, j.name, 
                                                j.molType, j.description)
                    if (j.molType == 'c') :
                        print "%s(%s_i%s):%s" % (reference, i.name, j.name, 
                                                 j.proteinDescription)
            #for                                                
        if ';' in RD.record.description :
            print "%s:%c.[%s]" % (reference, RD.record.molType, 
                                  RD.record.description)
        else :
            print "%s:%c.%s" % (reference, RD.record.molType, 
                                RD.record.description)

        #pd = O.getOutput("proteindescription")
        #if pd :
        #    if O.getOutput("altprotein") :
        #        print "%s:p.(0)" % reference
        #    else :
        #        print "%s:%s" % (reference, pd[0])
        ##if

        op = O.getOutput("oldprotein")
        if op :
            print "\n<b>Old protein:</b>"
            __bprint(op[0])
            print
        #if
        np = O.getOutput("newprotein")
        if np :
            print "\n<b>New protein:</b>"
            __bprint(np[0])
            print
        #if
        ap = O.getOutput("altprotein")
        if ap :
            print "\n<b>Alternative protein using start codon %s:</b>" % \
                O.getOutput("altstart")[0]
            __bprint(ap[0])
            print
        #if

        print
        for i in RD.record.geneList :
            for j in i.transcriptList :
                print "%s_v%s = %s = %s" % (i.name, j.name, j.transcriptID,
                                            j.locusTag)
                print "%s_i%s = %s = %s" % (i.name, j.name, j.proteinID,
                                                j.locusTag)
            #for
    #if
    ### OUTPUT BLOCK ###
    del O
#main

if __name__ == "__main__" :
    main(sys.argv[1])
#if
