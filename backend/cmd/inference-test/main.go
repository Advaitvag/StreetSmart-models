package main

import (
	"fmt"
	"log"

	ort "github.com/yalue/onnxruntime_go"
)

func main() {
	fmt.Println("Initializing ONNX Runtime...")

	// Windows runtime for onnx
	ort.SetSharedLibraryPath("lib/onnxruntime.dll")

	err := ort.InitializeEnvironment()
	if err != nil {
		log.Fatal(err)
	}
	defer ort.DestroyEnvironment()

	fmt.Println("ONNX Runtime initialized successfully!")
}
