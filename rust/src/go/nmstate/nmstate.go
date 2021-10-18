package nmstate

// #cgo CFLAGS: -g -Wall
// #cgo LDFLAGS: -lnmstate
// #include <nmstate.h>
// #include <stdlib.h>
import "C"
import (
	"fmt"
	"io"
	"time"
)

type Nmstate struct {
	timeout	    uint
	logsWriter  io.Writer
	flags	    byte
}

const (
	kernelOnly = 1 << iota
	noVerify
	includeStatusData
	includeSecrets
	noCommit
)

func New(options ...func(*Nmstate)) *Nmstate {
	return &Nmstate{}
}

func WithTimeout(timeout time.Duration) func(*Nmstate) {
	return func(n *Nmstate) {
		n.timeout = uint(timeout.Seconds())
	}
}

func WithLogsWritter(log_writter io.Writer) func(*Nmstate) {
	return func(n *Nmstate) {
		n.logsWriter = log_writter
	}
}

func WithKernelOnly() func(*Nmstate) {
	return func(n *Nmstate) {
		n.flags = n.flags | kernelOnly
	}
}

func WithNoVerify() func(*Nmstate) {
	return func(n *Nmstate) {
		n.flags = n.flags | noVerify
	}
}

func WithIncludeStatusData() func(*Nmstate) {
	return func(n *Nmstate) {
		n.flags = n.flags | includeStatusData
	}
}

func WithIncludeSecrets() func(*Nmstate) {
	return func(n *Nmstate) {
		n.flags = n.flags | includeSecrets
	}
}

func WithNoCommit() func(*Nmstate) {
	return func(n *Nmstate) {
		n.flags = n.flags | noCommit
	}
}

// Retrieve the network state in json format. This function returns the current
// network state or an error.
func (n *Nmstate) RetrieveNetState() (string, error) {
	var (
		state    *C.char
		log      *C.char
		err_kind *C.char
		err_msg  *C.char
	)
	rc := C.nmstate_net_state_retrieve(C.uint(n.flags), &state, &log, &err_kind, &err_msg)
	defer func() {
		C.nmstate_net_state_free(state)
		C.nmstate_err_msg_free(err_msg)
		C.nmstate_err_kind_free(err_kind)
		C.nmstate_log_free(log)
	}()
	_, err := io.WriteString(n.logsWriter, C.GoString(log))
	if err != nil {
		return "", fmt.Errorf("failed writting logs: %v", err)
	}
	if rc != 0 {
		return "", fmt.Errorf("failed retrieving nmstate net state with rc: %d, err_msg: %s, err_kind: %s", rc, C.GoString(err_msg), C.GoString(err_kind))
	}
	return C.GoString(state), nil
}

// Apply the network state in json format. This function returns the applied
// network state or an error.
func (n *Nmstate) ApplyNetState(state string) (string, error) {
	var (
		c_state  *C.char
		log      *C.char
		err_kind *C.char
		err_msg  *C.char
	)
	c_state = C.CString(state)
	rc := C.nmstate_net_state_apply(C.uint(n.flags), c_state, C.uint(n.timeout), &log, &err_kind, &err_msg)

	defer func() {
		C.nmstate_net_state_free(c_state)
		C.nmstate_err_msg_free(err_msg)
		C.nmstate_err_kind_free(err_kind)
		C.nmstate_log_free(log)
	}()
	_, err := io.WriteString(n.logsWriter, C.GoString(log))
	if err != nil {
		return "", fmt.Errorf("failed writting logs: %v", err)
	}
	if rc != 0 {
		return "", fmt.Errorf("failed applying nmstate net state %s with rc: %d, err_msg: %s, err_kind: %s", state, rc, C.GoString(err_msg), C.GoString(err_kind))
	}
	return state, nil
}

// Commit the checkpoint path provided. This function returns the committed
// checkpoint path or an error.
func (n *Nmstate) CommitCheckpoint(checkpoint string) (string, error) {
	var (
		c_checkpoint *C.char
		log	     *C.char
		err_kind     *C.char
		err_msg      *C.char
	)
	c_checkpoint = C.CString(checkpoint)
	rc := C.nmstate_checkpoint_commit(c_checkpoint, &log, &err_kind, &err_msg)

	defer func() {
		C.nmstate_checkpoint_free(c_checkpoint)
		C.nmstate_err_msg_free(err_msg)
		C.nmstate_err_kind_free(err_kind)
		C.nmstate_log_free(log)
	}()
	_, err := io.WriteString(n.logsWriter, C.GoString(log))
	if err != nil {
		return "", fmt.Errorf("failed writting logs: %v", err)
	}
	if rc != 0 {
		return "", fmt.Errorf("failed commiting checkpoint %s with rc: %d, err_msg: %s, err_kind: %s", checkpoint, rc, C.GoString(err_msg), C.GoString(err_kind))
	}
	return checkpoint, nil
}

// Rollback to the checkpoint provided. This function returns the checkpoint
// path used for rollback or an error.
func (n *Nmstate) RollbackCheckpoint(checkpoint string) (string, error) {
	var (
		c_checkpoint *C.char
		log	     *C.char
		err_kind     *C.char
		err_msg      *C.char
	)
	c_checkpoint = C.CString(checkpoint)
	rc := C.nmstate_checkpoint_rollback(c_checkpoint, &log, &err_kind, &err_msg)

	defer func() {
		C.nmstate_checkpoint_free(c_checkpoint)
		C.nmstate_err_msg_free(err_msg)
		C.nmstate_err_kind_free(err_kind)
		C.nmstate_log_free(log)
	}()
	_, err := io.WriteString(n.logsWriter, C.GoString(log))
	if err != nil {
		return "", fmt.Errorf("failed writting logs: %v", err)
	}
	if rc != 0 {
		return "", fmt.Errorf("failed when doing rollback checkpoint %s with rc: %d, err_msg: %s, err_kind: %s", checkpoint, rc, C.GoString(err_msg), C.GoString(err_kind))
	}
	return checkpoint, nil
}