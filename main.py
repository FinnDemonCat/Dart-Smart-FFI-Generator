import io
import re

TypesMap = {
	"char": ("Uint8", "int"),
	"char*": ("Pointer<Utf8>", "Pointer<Utf8>"),
	"unsigned char*": ("Pointer<Utf8>", "Pointer<Utf8>"),
	"int": ("Int32", "int"),
	"int*": ("Pointer<Int32>", "Pointer<Int32>"),
	"unsigned int": ("Uint32", "int"),
	"long long": ("Int64", "int"),
	"unsigned long long": ("Uint64", "int"),
	"float": ("Float", "double"),
	"double": ("Double", "double"),
	"void": ("Void", "void"),
	"void*": ("Pointer<Void>", "Pointer<Void>"),
	"bool": ("Bool", "bool") 
}

PointerCast = "Pointer<{var}>"
# RLAPI type funcName(types)
# Pattern = r"(?:\w+\s+)(\w+)\s+(\w+)\s*\((.*?)\)"
# RLAPI Color *LoadImageColors(Image image);

# Ignore trailing spaces, then capture the first two space separted words, followed by a space and everything in paranthesis
Pattern = r"(?:\w+\s+)([\w\*]+)\s+([\w\*]+)\s*\((.*?)\)"

OutputFile = "mappings.dart"
OutputName = "_{funcName}{sufix}"
OutputPattern = "typedef {name} = {CType} Function({params});"

while True:
	function = input()

	if (function == "break"):
		break
	elif(len(function) < 1):
		break

	for line in function.split('\n'):
		if not line or line.startswith('//') or line.startswith('#'):
			continue

		line = line.split(';')[0].strip()
		matches = re.search(Pattern, line)

		if (matches == None):
			continue

		with open(file=OutputFile, mode='a') as file:
			functionTypeC = matches.group(1)
			functionTypeDart = ""
			functionName = matches.group(2)
			params = matches.group(3)

			if (functionName.startswith('*')):
				functionTypeC += '*'
				functionName = functionName[1:]

			mapping = TypesMap.get(functionTypeC)
			if (mapping is None):
				if (functionTypeC.endswith('*')): functionTypeC = PointerCast.format(var='_' + functionTypeC.replace('*', ''))
				else: functionTypeC = "_{type}".format(type=functionTypeC)

				functionTypeDart = functionTypeC
			else:
				functionTypeC = mapping[0]
				functionTypeDart = mapping[1]
				
			
			paramsList = []

			# Extracting types from parameters declaration into a list
			for p in params.split(','):
				# Cleaning extra WhiteSpace and splitting last name from type 
				parts = p.strip().rsplit(maxsplit=1)

				type = ""
				name = ""
				if (len(parts) == 2):
					type, name = parts;

					# Case asterics pointer declaration it's with the name
					# instead of type
					if (name.startswith('*')):
						type += '*'
						name = name[1:]
					
				type = type.replace('const', '').strip()

				mapping = TypesMap.get(type, None)
				if (mapping is None):
					if (type.endswith('*')): type = PointerCast.format(var='_' + type.replace('*', '').strip())
					else: type = "_{type}".format(type=type)
				
				paramsList.append(type)
			
			cOutputParams = [TypesMap.get(t, (t, t))[0] for t in paramsList]
			dartOutputParams = [TypesMap.get(t, (t, t))[1] for t in paramsList]
			
			# OutputName = "_{funcName}{sufix}"
			#"typedef _{name} = {CType}Function({params})"
			cName = OutputName.format(funcName=functionName, sufix="Ray")
			dartName = OutputName.format(funcName=functionName, sufix="Dart")

			# print('\n', file=file)
			print(OutputPattern.format(name=cName, CType=functionTypeC, params=", ".join(cOutputParams)), end='\n', file=file)
			print(OutputPattern.format(name=dartName, CType=functionTypeDart, params=", ".join(dartOutputParams)), end='\n', file=file)
			print(f"final _{functionName[0].lower() + functionName[1:]} = _dylib.lookupFunction<{cName}, {dartName}>('{functionName}');", file=file, end='\n\n')
