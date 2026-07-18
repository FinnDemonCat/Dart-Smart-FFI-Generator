import re
import sys

from typing import TextIO
from typing import TypeAlias
from typing import cast
from functools import reduce

def lowerCamelCase(name: str):
	return name[:1].lower() + name[1:]

funcParse: TypeAlias = tuple[str, str, str, str, list[tuple[str, str, str]]]

# Read file with crop of structs to transform into class
# Search tags to automatically define methods

# How the class member should look in the struct mapping
mappingTemplate = "{annotation}external {type} {name};"
# Types annotation relation
typesAnnotation = {
	# Base Types
	"void": "Void",
	"bool": "Bool",
	"char": "UInt8",
	"const char": "Utf8",
	"signed char": "UInt8",
	"unsigned char": "Uint8",
	"short": "Int16",
	"signed short": "Int16",
	"short int": "Int16",
	"signed short int": "Int16",
	"unsigned short": "Uint16",
	"unsigned short int": "Uint16",
	"int": "Int32",
	"signed int": "Int32",
	"unsigned int": "Uint32",
	"long": "Long",
	"signed long": "Long",
	"long int": "Long",
	"signed long int": "Long",
	"unsigned long": "UnsignedLong",
	"unsigned long int": "UnsignedLong",
	"long long": "Int64",
	"signed long long": "Int64",
	"long long int": "Int64",
	"signed long long int": "Int64",
	"unsigned long long": "Uint64",
	"unsigned long long int": "Uint64",

	# Floats
	"float": "Float",
	"double": "Double",

	# Fixed sizes (<stdint.h>) 
	"int8_t": "Int8",
	"uint8_t": "Uint8",
	"int16_t": "Int16",
	"uint16_t": "Uint16",
	"int32_t": "Int32",
	"uint32_t": "Uint32",
	"int64_t": "Int64",
	"uint64_t": "Uint64",
}
# C type convertion
typesEquivalent = {
	"void": "void",
	"bool": "bool",
	"char": "int",
	"signed char": "int",
	"unsigned char": "int",
	"short": "int",
	"signed short": "int",
	"short int": "int",
	"signed short int": "int",
	"unsigned short": "int",
	"unsigned short int": "int",
	"int": "int",
	"signed int": "int",
	"unsigned int": "int",
	"long": "int",
	"signed long": "int",
	"long int": "int",
	"signed long int": "int",
	"unsigned long": "int",
	"unsigned long int": "int",
	"long long": "int",
	"signed long long": "int",
	"long long int": "int",
	"signed long long int": "int",
	"unsigned long long": "int",
	"unsigned long long int": "int",
	"float": "double",
	"double": "double",
	"int8_t": "int",
	"uint8_t": "int",
	"int16_t": "int",
	"uint16_t": "int",
	"int32_t": "int",
	"uint32_t": "int",
	"int64_t": "int",
	"uint64_t": "int",
	"size_t": "int",
	"intptr_t": "int",
	"uintptr_t": "int",
	"ptrdiff_t": "int",
	"char*": "Pointer<Utf8>",
	"const char*": "Pointer<Utf8>",
	"unsigned char*": "Pointer<Uint8>",
	"const unsigned char*": "Pointer<Uint8>"
}

# ===================================================================================================================================

# Process a function string into a tuple (funcName, funcType, funcEquivalent, funcComment, [(paramName, paramType, paramEquivalent)])
def functKeywords(functionStr: str) -> funcParse:
	funcName = ''
	funcComment = ''
	funcType = ''
	funcEquivalent = ''
	params = []

	functionRe = re.match(r'(?P<type>[\w\s\*]+?)\s*(?P<name>\w+?)\s*\((?P<parameters>[\s\S]+?)\)\s*;\s*(?://\s*(?P<comment>[^\n]+))?', string=functionStr)
	
	if (functionRe):
		funcName = functionRe.group('name')
		funcComment = functionRe.group('comment') or ''
		funcType = functionRe.group('type').replace(' *', '*')

		isPointer = False

		if (funcType.endswith('*')):
			isPointer = True

		# If not found in maps, assume its a lib struct
		funcEquivalent = typesEquivalent.get(funcType)
		funcType = typesAnnotation.get(funcType)

		if (funcEquivalent is None and isPointer):
			funcType = functionRe.group('type').replace('*', '').strip()
			funcType = funcEquivalent = F'Pointer<{typesAnnotation.get(funcType) or F'_{funcType}'}>'
		elif (funcEquivalent is None and isPointer is False):
			funcType = funcEquivalent = F'_{functionRe.group('type')}'
		if (funcEquivalent is None):
			funcEquivalent = ''
		if (funcType is None):
			funcType = funcEquivalent

		funcParametersRe = functionRe.group('parameters')
		for param in funcParametersRe.split(','):
			param = param.strip()

			# Extracting param type and name
			paramRe = re.match(r'(?s)(?P<type>[\w\s\*]+)\s+(?P<name>[\w\*]+)$', string=param)
			if (paramRe is None):
				continue

			varName = paramRe.group('name')
			varType = paramRe.group('type')

			isPointer = False

			if (varType.endswith('*') or varName.startswith('*')):
				varName = varName.replace('*', '')
				varType += '*'
				isPointer = True

			varEquivalent = typesEquivalent.get(varType)
			varType = typesAnnotation.get(varType)

			if (varEquivalent is None and isPointer is True):
				varType = paramRe.group('type').replace('*', '')
				varEquivalent = varType = F'Pointer<{typesAnnotation.get(varType) or F'_{varType}'}>'
			# If not found in types relation, assume its a struct
			elif (varEquivalent is None and isPointer is False):
				varEquivalent = varType = F'_{paramRe.group('type')}'
			if (varType is None):
				varType = varEquivalent
			
			params.append((varName, varEquivalent, varType))
	
	return (funcName, funcType, funcEquivalent, funcComment, params)
# ===================================================================================================================================

def paramAcessor(varType: str) -> tuple[str, str]:
	varAcessor = ''

	if (varRE := re.match(r'Pointer<_(?P<extract>\w+?)>', string=varType)):
		varAcessor = '.pointer'
		varType = varRE.group('extract')
	elif (varType[0] == '_'):
		varAcessor = '.ref'
		varType = varType.replace('_', '')
	elif (varType == 'double'):
		varAcessor = '.toDouble()'
		varType = 'num'
	
	return (varType, varAcessor)

# ===================================================================================================================================

def codeTitle(outputStream: TextIO, title: str):
    outputStream.write(F'// {'':=^120}\n')
    outputStream.write(F'// {F' {title} ':^120}\n')
    outputStream.write(F'// {'':=^120}\n\n')

# ===================================================================================================================================

inputStream: TextIO
outputStream: TextIO

try:
	inputStream = open('native_code_input.c.txt', 'r', encoding='utf-8')
except Exception as e:
	print("Could not open native_code_input.c.txt!")
	sys.exit(-1)

try:
	outputStream = open('dart_ffi_output.dart.txt', 'w+', encoding='utf-8')
except Exception as e:
	print("Could not open dart_ffi_output.dart.txt!")
	sys.exit(-1)

# ========== Reading file contents to build wrapper =============
fileContent = inputStream.read()

structRe = re.search(r'(?s)(?:\/\/\s*(?P<doc_comment>.*?)\n)?\s*typedef\s+struct\s+(?P<name>\w+)\s+\{(?P<content>.*?)\}', string=fileContent)
if (structRe is None):
	raise ValueError("Could not find typedef")

structName = structRe.group('name')
structComment = structRe.group('doc_comment') or ''
structMembers = [] # (varName, typeEquivalent, typeAnnotation, varComment)

codeTitle(outputStream, structName)

# ================ Building struct wrapper =====================

for param in (structRe.group('content') or '').strip().split('\n'):
	param = param.strip()
	memberRe = re.match(r'(?P<type>[\w\s\*]+?)\s+(?P<name>[\w\*]+)\s*;\s*(?://\s*(?P<comment>.*))?', string=param)
		
	if (memberRe):
		varType = memberRe.group('type')
		varName = memberRe.group('name')
		varComment = memberRe.group('comment') or ''

		isPointer = False
		isArray = False
		isNested = False

		# If its a pointer
		if (varName.startswith('*') or varType.endswith('*')):
			# Remove asterisc, mark as pointer
			varName = varName.replace('*', '')
			varType = varType.replace('*', '')
			isPointer = True
		# Else if its an array
		elif (re.search(r'[\d]', string=varName)):
			varName = re.sub(r'\[\d\]', '', string=varName)
			isArray = True

		varAnnotation = typesAnnotation.get(varType) or ''
		varEquivalent = typesEquivalent.get(varType) or '_'+varType
		
		# Formatting variable type equivalent
		if (isPointer):
			varEquivalent = F'Pointer<{varAnnotation or '_'+varType}>'
			varAnnotation = ''
		elif (isArray):
			varEquivalent = F'Array<{varAnnotation or '_'+varType}>'

			arrayRe = re.search(r'\[(?P<size>\d)\]', string=memberRe.group('name'))
			if (arrayRe is None): continue

			varAnnotation = F'Array({arrayRe.group('size')}) '
		# Adding subfix
		elif (len(varAnnotation) > 0):
			varAnnotation += '() '
		
		structMembers.append((varName, varEquivalent, varAnnotation, varComment))

# annotation equivalent name comment

# Calculating comment space aligment
commentSpacing = reduce(lambda acc, elem: max(acc, len(F'{elem[2]}external {elem[1]} {elem[0]};')), structMembers, 0)
outputStream.write(F'/// {structComment}\n' if len(structComment) > 0 else '')
outputStream.write(F"final class _{structName} extends Struct {{\n")

for index in range(len(structMembers)):
	varName, varEquivalent, varAnnotation, varComment = structMembers[index]

	line = F'\t{varAnnotation}external {varEquivalent} {varName};'

	trailingSpace = commentSpacing - len(line) + 1
	outputStream.write(line)
	if (varComment != ''):
		outputStream.write(F'{' ':>{trailingSpace}}// {varComment}')
	outputStream.write('\n')

outputStream.write("}\n\n")

# ================= Processing functions ====================

isPointer = False
isArray = False
isNested = False

# (funcName, funcType, funcEquivalent, funcComment, [(paramName, paramType, paramEquivalent)])
mainConstructor: funcParse | None = None
deconstructor: funcParse | None = None
namedConstructors = []
methods = []

constructorRe = re.search(r'(?s)#\s*Constructor(?:[^\n]*)(?P<content>.*?)(?=\n#|\Z)', string=fileContent)
if (constructorRe):
	function = constructorRe.group('content').strip()
	mainConstructor = functKeywords(function)
else:
	print("No constuctor function was found, the script will create one")

namedRe = re.search(r'(?s)#\s*Named Constructor(?:[^\n]*)(?P<content>.*?)(?=\n#|\Z)', string=fileContent)
if (namedRe):
	for function in namedRe.group('content').strip().split('\n'):
		namedConstructors.append(functKeywords(function))
else:
	print("No named constructors were found")

methodsRe = re.search(r'(?s)#\s*Methods\s*(?:[^\n]*)(?P<content>.*?)(?=\n#|\Z)', string=fileContent)
if (methodsRe):
	for function in methodsRe.group('content').strip().split('\n'):
		methods.append(functKeywords(function))
else:
	print("No methods were found")

deconstructorRE = re.search(r'(?s)#\s*Deconstructor\s*(?:[^\n]*)(?P<content>.*?)(?=\n#|\Z)', string=fileContent)
if (deconstructorRE):
	deconstructor = functKeywords(deconstructorRE.group('content').strip())
else:
	print("No deconstructor function found")

for function in filter(None, [mainConstructor] + namedConstructors + [deconstructor] + methods):
	funcName, funcEquivalent, funcAnnotation, funcComment, params = function

	if (funcComment != ''):
		outputStream.write(F'// {funcComment}\n')
	
	outputStream.write(F'typedef _{funcName}C    = {funcEquivalent} Function({', '.join(t[2] for t in params)});\n')
	outputStream.write(F'typedef _{funcName}Dart = {funcAnnotation} Function({', '.join(t[1] for t in params)});\n')
	outputStream.write(F'final _{lowerCamelCase(funcName)} = _dylib.lookupFunction<_{funcName}C, _{funcName}Dart>(\'{funcName}\');\n\n')

if (deconstructor):
	_, _, _, funcComment, _ = deconstructor

	if (funcComment != ''):
		outputStream.write(F'// {funcComment}\n')
	
	outputStream.write(F'typedef _Free{structName}C    = Void Function(Pointer<Void> token);\n')
	outputStream.write(F'typedef _Free{structName}Dart = void Function(Pointer<Void> token);\n')
	outputStream.write(F'final _free{structName} = _dyReleaseLib.lookup<NativeFunction<_Free{structName}C>>(\'Free{structName}\');\n\n')

codeTitle(outputStream, 'Wrapper Class')

# ================= Building Wrapper Class =====================

outputStream.write(F'{F'/// {structComment}' if len(structComment) > 0 else ''}\n')
outputStream.write(F'class {structName} extends NativeWrapper<_{structName}> {{\n')
outputStream.write(F'\t_{structName} get ref => pointer.ref;\n')
outputStream.write(F'\tset ref(_{structName} value) => pointer.ref = value;\n')
outputStream.write(F'\n')

# == Writing setters & getters ==
classGetters = ''
classSetters = ''

for param in structMembers:
	# Umpackign the tuple
	varName, varEquivalent, varAnnotation, varComment = param

	classGetters += F'\t{F'/// {varComment}\n\t' if len(varComment) > 0 else ''}{varEquivalent} get {varName} => ref.{varName};\n'

	varEquivalent, varAcessor = paramAcessor(varEquivalent)
	classSetters += F'\tset {varName}({varEquivalent if varEquivalent != 'double' else 'num'} value) => ref.{varName} = value{varAcessor};\n'
	
outputStream.write(F'{classGetters}\n{classSetters}\n')

# == Writing wrapper type init ==

outputStream.write('\t// ignore: unused_element_parameter, unused_element\n')
outputStream.write(F'\t{structName}._Encapsulate(super.pointer,{{ super.IsOwner, super.length }}): super.fromAddress() {{\n')
outputStream.write(F'\t\tif (IsOwner)\n\t\t\t_nativeFinalizer.attach(this, pointer, detach: this);\n')
outputStream.write(F'\t}}\n\n')

outputStream.write('\t// ignore: unused_element_parameter, unused_element\n')
outputStream.write(F'\t{structName}._Recieve(_{structName} result): super(sizeOf<_{structName}>()) {{\n')
outputStream.write(F'\t\tref = result;\n\t\t_nativeFinalizer.attach(this, pointer, detach: this);\n')
outputStream.write(F'\t}}\n\n')

# ===== Writing constructor =====
# (funcName, funcType, funcEquivalent, funcComment, [(paramName, paramType, paramEquivalent)])
# mainConstructor: funcParse | None = None

outputStream.write(F'\t// {' Constructor ':=^86}\n\n')

paramsRelation = []
params = (mainConstructor[4] if mainConstructor else structMembers)

for param in params:
	varName, varEquivalent, *_ = param

	varName = cast(str, varName)
	varEquivalent = cast(str, varEquivalent)
	varEquivalent, varAcessor = paramAcessor(varEquivalent)
	
	paramsRelation.append((varName, varEquivalent, varAcessor))

if (mainConstructor):
	outputStream.write(F'\tfactory {structName}({', '.join(F'{t[1]} {t[0]}' for t in paramsRelation)}) {{\n')
	outputStream.write(F'\t\t_{structName} result = _{lowerCamelCase(funcName)}({', '.join(t[0] for t in paramsRelation)});\n\n')
	outputStream.write(F'\t\t{structName} {structName[:1].lower()}{structName[1:]} = {structName}._Recieve(result);\n')
	outputStream.write(F'\t\treturn {structName[:1].lower()}{structName[1:]};\n')
	outputStream.write(F'\t}}\n\n')
else:
	outputStream.write(F'\t{structName}({', '.join(F'{t[1]} {t[0]}' for t in paramsRelation)}) : super(sizeOf<_{structName}>()) {{\n')
	outputStream.write(F'\t\tref\n{'\n'.join('\t\t\t..{} = {}{}'.format(t[0], t[0], t[2]) for t in paramsRelation)};\n\n')
	outputStream.write(F'\t\t_nativeFinalizer.attach(this, pointer, detach: this);\n')
	outputStream.write(F'\t}}\n\n')

# == Writing Named constructor ==
if (namedConstructors):
	outputStream.write(F'\t// {' Named Constructor ':=^86}\n\n')

# (funcName, funcType, funcEquivalent, funcComment, [(paramName, paramEquivalent, paramEAnnotation)])
for func in namedConstructors:
	funcName, funcType, funcEquivalent, funComment, params = func

	paramsRelation = []

	for param in params:
		varName, varEquivalent, *_ = param

		varName = cast(str, varName)
		varEquivalent = cast(str, varEquivalent)
		varEquivalent, varAcessor = paramAcessor(varEquivalent)
		
		paramsRelation.append((varName, varEquivalent, varAcessor))

	if (funcComment != ''):
		outputStream.write(F'\t/// {funcComment}\n')
	
	outputStream.write(F'\tfactory Image.{funcName.replace(structName, '')}({', '.join(F'{t[1]} {t[0]}' for t in paramsRelation)}) {{\n')
	outputStream.write(F'\t\t_{structName} result = _{lowerCamelCase(funcName)}({', '.join(F'{t[0]}{t[2]}' for t in paramsRelation)});\n')
	outputStream.write(F'\t\t{structName} {lowerCamelCase(structName)} = {structName}._Recieve(result);\n')
	outputStream.write(F'\t\treturn {lowerCamelCase(structName)};\n')
	outputStream.write(F'\t}}\n\n')

# ===== Writing the Methods =====

outputStream.write(F'\t// {' Methods ':=^86}\n\n')

# (funcName, funcType, funcEquivalent, funcComment, [(paramName, paramType, paramEquivalent)])
for method in methods:
	funcName, funcType, funcEquivalent, funcComment, params = method
	funcName = cast(str, funcName)
	funcType = cast(str, funcType)
	funcEquivalent = cast(str, funcEquivalent)
	funcComment = cast(str, funcComment)

	# varName, varEquivalent, varAcessor
	paramsRelation = []

	for param in params:
		varName, varEquivalent, *_ = param

		varName = cast(str, varName)
		varEquivalent = cast(str, varEquivalent)
		varEquivalent, varAcessor = paramAcessor(varEquivalent)
		
		paramsRelation.append((varName, varEquivalent, varAcessor))

	if (funcComment != ''):
		outputStream.write(F'\t/// {funcComment}\n')
	
	isPointer = (paramsRelation[0][2] == '.pointer')
	
	outputStream.write(F'\t{funcEquivalent} {funcName.replace(structName, '')}({', '.join(F'{t[1]} {t[0]}' for t in paramsRelation[1:])})')
	outputStream.write(F' => _{lowerCamelCase(funcName)}({'pointer' if isPointer else 'ref'}{', ' if len(paramsRelation) > 1 else ''}{', '.join(F'{t[0]}{t[2]}' for t in paramsRelation[1:])});\n')

outputStream.write(F'\n')

# ==== Writing Deconstructor ====

outputStream.write(F'\t// {' Deconstructor ':=^86}\n\n')

outputStream.write(F'\tstatic final _nativeFinalizer = NativeFinalizer(_free{structName});\n\n')
if (deconstructor):
	funcName, funcType, funcEquivalent, funcComment, params = deconstructor
	if (funcComment != ''):
		outputStream.write(F'\t// {funcComment}\n')
	
	varName, varEquivalent, varAcessor = params[0]
	outputStream.write(F'\t@override\n\tFree() {{\n')
	outputStream.write(F'\t\t_{lowerCamelCase(funcName)}({varAcessor});\n')
	outputStream.write(F'\t\t_nativeFinalizer.detach(this);\n\t\tsuper.Free();\n\t}}\n\n')

	outputStream.write(F'\t\\*\n')
	outputStream.write(F'\t__declspec(dllexport) void Free{structName}(void* pointer){{\n')
	outputStream.write(F'\t\tif (pointer == NULL) return;\n')
	outputStream.write(F'\n\t\t{structName} {lowerCamelCase(structName)} = *({structName}*)pointer;\n')
	outputStream.write(F'\t\t{funcName}({lowerCamelCase(structName)});\n\t}}\n')
	outputStream.write(F'\t*\\\n')

# ====================== Closing File ==========================

outputStream.write(F'}}')
inputStream.close()
outputStream.close()