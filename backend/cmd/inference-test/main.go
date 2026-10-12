package main

import (
	"fmt"
	"log"
	"os"
	"runtime"

	ort "github.com/yalue/onnxruntime_go"

	"streetsmart-backend/internal/inference"
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

	detector, err := inference.NewDetector("models/pothole.onnx")
	if err != nil {
		log.Fatal("Failed to load detector: ", err)
	}
	defer detector.Close()

	fmt.Println("Pothole detector loaded successfully")

	predictions, err := detector.Run()
	if err != nil {
		log.Fatal("Inference failed: ", err)
	}

	fmt.Printf("Inference succeeded! Received %d values.\n", len(predictions))
	fmt.Printf("First 10 values: %v\n", predictions[:10])
}
