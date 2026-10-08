package main

import (
	"fmt"
	"log"
	"os"
	"runtime"

	ort "github.com/yalue/onnxruntime_go"
)

func libPath() string {
	if v := os.Getenv("ORT_LIB_PATH"); v != "" {
		return v
	}
	if runtime.GOOS == "linux" {
		return "lib/libonnxruntime.so.1.29.0"
	}
	if runtime.GOOS == "windows" {
		return "lib/onnxruntime.dll"
	}
	log.Fatalf("unsupported GOOS: %s (only windows + linux)", runtime.GOOS)
	return ""
}

func main() {
	fmt.Println("Initializing ONNX Runtime...")

	ort.SetSharedLibraryPath(libPath())

	err := ort.InitializeEnvironment()
	if err != nil {
		log.Fatal(err)
	}
	defer ort.DestroyEnvironment()

	fmt.Println("ONNX Runtime initialized successfully!")
}
