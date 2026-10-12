package inference

import (
	ort "github.com/yalue/onnxruntime_go"
)

const (
	inputName = "images"

	outputName   = "output"
	output80Name = "onnx::Reshape_1394"
	output40Name = "onnx::Reshape_1421"
	output20Name = "onnx::Reshape_1448"
)

type Detector struct {
	session *ort.AdvancedSession   // Session to run inference
	input   *ort.Tensor[float32]   // Holds the input image tensor
	outputs []*ort.Tensor[float32] // Holds the model's four output tensors
}

// Constructor function, returns detector object after loading
// ONNX model.
func NewDetector(modelPath string) (*Detector, error) {
	// allocate input tensor
	input, err := ort.NewTensor[float32](
		//  input shape is [batch, channels, height, width]
		// [1 image, 3 color channels (RGB), 640x640 pixels]
		ort.NewShape(1, 3, 640, 640),

		// Allocate float32 values to hold every pixel channel.
		// Initialized to 0, will be filled with image data downstream.
		make([]float32, 1*3*640*640),
	)
	if err != nil {
		return nil, err
	}

	// Buffer for model's primary output: 8400 predictions
	// We will probably only need this output,
	// but we are allocating for all 4 output heads in case
	// or for future optimizations.
	output, err := ort.NewEmptyTensor[float32](ort.NewShape(1, 5, 8400))
	if err != nil {
		input.Destroy()
		return nil, err
	}

	// Allocate first raw output head, 80x80 spatial grid
	output80, err := ort.NewEmptyTensor[float32](ort.NewShape(1, 5, 80, 80))
	if err != nil {
		input.Destroy()
		output.Destroy()
		return nil, err
	}

	// Allocate the second raw output head, 40x40 grid
	output40, err := ort.NewEmptyTensor[float32](ort.NewShape(1, 5, 40, 40))
	if err != nil {
		input.Destroy()
		output.Destroy()
		output80.Destroy()
		return nil, err
	}

	// Allocate the third raw output head, 20x20 grid
	output20, err := ort.NewEmptyTensor[float32](ort.NewShape(1, 5, 20, 20))
	if err != nil {
		input.Destroy()
		output.Destroy()
		output80.Destroy()
		output40.Destroy()
		return nil, err
	}

	// Now, let's initialize the session
	// and get crackin!
	session, err := ort.NewAdvancedSession(
		modelPath,
		[]string{inputName},
		[]string{outputName, output80Name, output40Name, output20Name},
		[]ort.Value{input},
		[]ort.Value{output, output80, output40, output20},
		nil,
	)
	if err != nil {
		input.Destroy()
		output.Destroy()
		output80.Destroy()
		output40.Destroy()
		output20.Destroy()
		return nil, err
	}

	// We will return a detector that owns teh session and its tensors
	return &Detector{
		session: session,
		input:   input,
		outputs: []*ort.Tensor[float32]{output, output80, output40, output20},
	}, nil
}

// Destructor function
func (d *Detector) Close() {
	if d.session != nil {
		d.session.Destroy()
	}

	if d.input != nil {
		d.input.Destroy()
	}

	for _, output := range d.outputs {
		if output != nil {
			output.Destroy()
		}
	}
}

// Run executes inference using the input tensor's current contents
func (d *Detector) Run() ([]float32, error) {
	// Run the model with the input and output tensors attached to
	// session object
	if err := d.session.Run(); err != nil {
		return nil, err
	}

	// Return raw values from model's primary output tensor
	// Probably the only head we'll need for now
	return d.outputs[0].GetData(), nil
}
