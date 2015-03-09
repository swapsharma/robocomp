#!/usr/bin/env python

from pyparsing import Word, alphas, alphanums, nums, OneOrMore, CharsNotIn, Literal, Combine
from pyparsing import cppStyleComment, Optional, Suppress, ZeroOrMore, Group, StringEnd, srange
from pyparsing import nestedExpr, CaselessLiteral

import sys, traceback, os

debug = False
#debug = True

from parseIDSL import *

class CDSLParsing:
	@staticmethod
	def fromFile(filename, verbose=False, includeIncludes=True):
		# Open input file
		#inputText = "\n".join([line for line in open(filename, 'r').read().split("\n") if not line.lstrip(" \t").startswith('//')])
		inputText = open(filename, 'r').read()
		try:
			ret = CDSLParsing.fromString(inputText)
		except:
			print 'Error reading', filename
			traceback.print_exc()
			print 'Error reading', filename
			sys.exit(1)
		ret['filename'] = filename
		return ret
	@staticmethod
	def fromString(inputText, verbose=False):
		if verbose: print 'Verbose:', verbose
		text = nestedExpr("/*", "*/").suppress().transformString(inputText) 

		semicolon = Suppress(Word(";"))
		quote     = Suppress(Word("\""))
		op        = Suppress(Word("{"))
		cl        = Suppress(Word("}"))
		opp       = Suppress(Word("("))
		clp       = Suppress(Word(")"))
		identifier = Word( alphas+"_", alphanums+"_" )

		# Imports
		idslImport  = Suppress(CaselessLiteral("import")) + quote +  CharsNotIn("\";").setResultsName('path') + quote + semicolon
		idslImports = OneOrMore(idslImport)
		# Communications
		implementsList = Group(CaselessLiteral('implements')    + identifier + ZeroOrMore(Suppress(Word(',')) + identifier) + semicolon)
		requiresList   = Group(CaselessLiteral('requires')      + identifier + ZeroOrMore(Suppress(Word(',')) + identifier) + semicolon)
		subscribesList = Group(CaselessLiteral('subscribesTo')  + identifier + ZeroOrMore(Suppress(Word(',')) + identifier) + semicolon)
		publishesList  = Group(CaselessLiteral('publishes')     + identifier + ZeroOrMore(Suppress(Word(',')) + identifier) + semicolon)
		communicationList = implementsList | requiresList | subscribesList | publishesList
		communications = Group( Suppress(CaselessLiteral("communications")) + op + ZeroOrMore(communicationList) + cl + semicolon)
		
		# Language
		language = Suppress(CaselessLiteral("language")) + (CaselessLiteral("cpp")|CaselessLiteral("python")) + semicolon
		# GUI
		gui = Group(Optional(Suppress(CaselessLiteral("gui")) + CaselessLiteral("Qt") + opp + identifier + clp + semicolon ))
		# additional options
		options = Group(Optional(Suppress(CaselessLiteral("options")) + identifier + ZeroOrMore(Suppress(Word(',')) + identifier) + semicolon))
		
		componentContents = communications.setResultsName('communications') & language.setResultsName('language') & gui.setResultsName('gui') & options.setResultsName('options')
		component = Suppress(CaselessLiteral("component")) + identifier.setResultsName("name") + op + componentContents.setResultsName("properties") + cl + semicolon		

		CDSL = idslImports.setResultsName("imports") + component.setResultsName("component")
		CDSL.ignore( cppStyleComment )
		tree = CDSL.parseString(text)
		return CDSLParsing.component(tree)

	@staticmethod
	def printComponent(component, start=''):
		# Component name
		print 'Component', component['name']
		# Imports
		print '\tImports:'
		for imp in component['imports']:
			print '\t\t', imp
		# Language
		print '\tLanguage:'
		print '\t\t', component['language']
		# GUI
		print '\tGUI:'
		print '\t\t', component['gui']
		# Communications
		print '\tCommunications:'
		print '\t\tImplements', component['implements']
		print '\t\tRequires', component['requires']
		print '\t\tPublishes', component['publishes']
		print '\t\tSubscribes', component['subscribesTo']

	@staticmethod
	def component(tree, start=''):
		component = {}
		
		# Set options
		component['options'] = []
		try:
			for op in tree['properties']['options']:
				component['options'].append(op.lower())
		except:
			traceback.print_exc()
		
		# Component name
		component['name'] = tree['component']['name']
		# Imports
		component['imports'] = []
		component['recursiveImports'] = []
		imprts = tree['imports']
		if 'agmagent' in component['options']:
			imprts = ['/robocomp/interfaces/IDSLs/AGMAgent.idsl', '/robocomp/interfaces/IDSLs/AGMExecutive.idsl', '/robocomp/interfaces/IDSLs/AGMCommonBehavior.idsl', '/robocomp/interfaces/IDSLs/AGMWorldModel.idsl']
			for i in tree['imports']:
				if not i in imprts:
					imprts.append(i)
		for imp in imprts:
			component['imports'].append(imp)
			
			#print 'moduleee', imp
			imp2 = imp.split('/')[-1]
			component['recursiveImports'] += [imp2]
			try:
				importedModule = IDSLParsing.gimmeIDSL(imp2)
			except:
				print 'Error reading IMPORT', imp2
				traceback.print_exc()
				print 'Error reading IMPORT', imp2
				os._exit(1)

			component['recursiveImports'] += [x for x in importedModule['imports'].split('#') if len(x)>0]
			#print 'moduleee', imp, 'done'
			
		#print component['recursiveImports']
		# Language
		component['language'] = tree['properties']['language'][0]
		# GUI
		component['gui'] = 'none'
		try:
			uiT = tree['properties']['gui'][0]
			uiI = tree['properties']['gui'][1]
			if uiT.lower() == 'qt' and uiI in ['QWidget', 'QMainWindow', 'QDialog' ]:
				component['gui'] = [ uiT, uiI ]
				pass
			else:
				print 'Wrong UI specification', tree['properties']['gui']
				sys.exit(1)
		except:
			pass
		

		# Communications
		component['implements']   = []
		component['requires']     = []
		component['publishes']    = []
		component['subscribesTo'] = []
		for comm in tree['properties']['communications']:
			if comm[0] == 'implements':
				for interface in comm[1:]: component['implements'].append(interface)
			if comm[0] == 'requires':
				for interface in comm[1:]: component['requires'].append(interface)
			if comm[0] == 'publishes':
				for interface in comm[1:]: component['publishes'].append(interface)
			if comm[0] == 'subscribesTo':
				for interface in comm[1:]: component['subscribesTo'].append(interface)
		# Handle options for communications
		if 'agmagent' in component['options']:
			if not 'AGMCommonBehavior' in component['implements']:
				component['implements']   = ['AGMCommonBehavior'] + component['implements']
			if not 'AGMAgentTopic' in component['publishes']:
				component['publishes']    = ['AGMAgentTopic']     + component['publishes']
			if not 'AGMExecutiveTopic' in component['subscribesTo']:
				component['subscribesTo'] = ['AGMExecutiveTopic'] + component['subscribesTo']



		return component

if __name__ == '__main__':
	CDSLParsing.fromFile(sys.argv[1])
