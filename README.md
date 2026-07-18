# C Struct to Dart FFI Binding Generator

Semi automatic Python script, built arround raylib C library code style conventions into Dart classes. Tailored for [Target]("https://github.com/FinnDemonCat/Target") Dart bindings project.

---

## 🛠 How to Prepare the Input File

The script takes only one input type. Firstly it reads `native_code_input.c.txt` and searches for the struct typedef, followed by the `# Constructor` tag, the `# Named Constructor` tag, the `# Methods` tag and finally the `# Deconstructor` tag:

1. **`typedef struct`**: The target C structure definition.
2. **`# Constructor`**: Defines functions that return a new instance of the struct (maps to the default Dart constructor).
3. **`# Named Constructor`**: Defines functions that return a new instance but map to Dart named constructors (e.g., `Image.fromMemory()`).
4. **`# Methods`**: Functions where the instance itself is passed around.
5. **`# Deconstructor`**: Functions meant to free up native memory resources.

---

## 📋 Input Specifications Example

Save your C header configurations like the example below (e.g., `native_code_input.c.txt`):

```c
// Image, pixel data stored in CPU memory (RAM)
typedef struct Image {
    void *data;             // Image raw data
    int width;              // Image base width
    int height;             // Image base height
    int mipmaps;            // Mipmap levels, 1 by default
    int format;             // Data format (PixelFormat type)
} Image;

# Constructor (New return instance)
Image LoadImage(const char *fileName);

# Named Constructor (New return instance)
Image LoadImageRaw(const char *fileName, int width, int height, int format, int headerSize);
Image LoadImageAnim(const char *fileName, int *frames);
Image LoadImageFromMemory(const char *fileType, const unsigned char *fileData, int dataSize);

# Methods (Assumes first parameter is the class instance)
bool IsImageValid(Image image);
void ImageClearBackground(Image *dst, Color color);
void ImageDrawPixel(Image *dst, int posX, int posY, Color color);

# Deconstructor
void UnloadImage(Image image);
```

## ⚙️ Generation Conventions
### 1. Method Binding (Parameter Hiding)

When a function is listed under Methods, the generator assumes that the first parameter is always the reference to the current instance.
- In C: void ImageClearBackground(Image *dst, Color color);
- In Dart: It becomes an extension/member method .clearBackground(Color color), automatically passing `this` behind the scenes.

### Ex:
```c
C:
// Clear image background with given color
void ImageClearBackground(Image *dst, Color color);

Dart:
/// Clear image background with given color
void ClearBackground(Color color) => _imageClearBackground(pointer, color.ref);
```

### 2. Constructor Conversion

- Default Constructor: Functions under `# Constructor` match the structure name directly (e.g., LoadImage $\rightarrow$ Image()).

- Named Constructors: tries to replace any match of the struct name in the function name (e.g., LoadImageRaw $\rightarrow$ Image.LoadRaw()).

- Deconstructors / FinalizersFunctions listed under `# Deconstructor` are wrapped into custom Free C handles receiving a void* pointer, safely mapping memory release mechanisms for Dart's native garbage collection lifecycle management.

## ⚙️ NativeWrapper class
[NativeWrapper]("https://github.com/FinnDemonCat/Target/blob/main/lib/native_wrapper/native_wrapper.dart") its a simple class created as a template for all these classes that wrap pointer instance of that struct.
