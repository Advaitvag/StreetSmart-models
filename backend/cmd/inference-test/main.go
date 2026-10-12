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

	if err := detector.LoadImage("test_inputs/pothole.jpg"); err != nil {
		log.Fatal("Failed to load image: ", err)
	}

	predictions, err := detector.Run()
	if err != nil {
		log.Fatal("Inference failed: ", err)
	}

	const numCandidates = 8400

	// Find the candidate with the highest value in the fifth output plane.
	scores := predictions[4*numCandidates : 5*numCandidates]

	bestIndex := 0
	maxScore := float32(0)

	for i, score := range scores {
		if score > maxScore {
			maxScore = score
			bestIndex = i
		}
	}

	// Read the four corresponding values from their separate output planes.
	x := predictions[bestIndex]
	y := predictions[numCandidates+bestIndex]
	w := predictions[2*numCandidates+bestIndex]
	h := predictions[3*numCandidates+bestIndex]

	// Draw the candidate box on a copy of the input image.
	err = inference.SaveVisualization(
		"test_inputs/pothole.jpg",
		"test_inputs/pothole-detection.jpg",
		x, y, w, h,
		maxScore,
	)
	if err != nil {
		log.Fatal("Failed to save visualization: ", err)
	}

	fmt.Printf("Inference succeeded! Received %d values.\n", len(predictions))
	fmt.Printf("First 10 values: %v\n", predictions[:10])
}
