use std::error::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
#[allow(dead_code)]
pub enum ErrorKind {
    InvalidArgument,
    PluginFailure,
    Bug,
    VerificationError,
    NotImplementedError,
    NotSupportedError,
    KernelIntegerRoundedError,
    DependencyError,
    PolicyError,
    PermissionError,
    SrIovVfNotFound,
}

#[cfg(feature = "query_apply")]
impl ErrorKind {
    pub(crate) fn can_retry(&self) -> bool {
        matches!(
            self,
            ErrorKind::PluginFailure
                | ErrorKind::Bug
                | ErrorKind::VerificationError
                | ErrorKind::SrIovVfNotFound
        )
    }

    // Indicate this error can be ignore at the final retry. This group of
    // errors is only used for verification retry. For example waiting
    // SR-IOV configure all the VFs
    pub(crate) fn can_ignore(&self) -> bool {
        matches!(self, ErrorKind::SrIovVfNotFound)
    }
}

impl Default for ErrorKind {
    fn default() -> Self {
        Self::Bug
    }
}

impl std::fmt::Display for ErrorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl std::fmt::Display for NmstateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if self.kind == ErrorKind::PolicyError {
            write!(
                f,
                "{}: {}\n| {}\n| {:.<5$}^\nError count: {}",
                self.kind,
                self.msg,
                self.line,
                "",
                self.position,
                self.error_count
            )
        } else {
            write!(
                f,
                "{}: {}\nError count: {}\nErrors: {:?}",
                self.kind, self.msg, self.error_count, self.errors
            )
        }
    }
}

impl Error for NmstateError {}

#[derive(Debug, Default, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub struct NmstateError {
    kind: ErrorKind,
    msg: String,
    line: String,
    position: usize,
    error_count: usize,
    errors: Vec<String>, // Store multiple error messages
}

impl NmstateError {
    // Constructor with default error_count = 1
    pub fn new(kind: ErrorKind, msg: String) -> Self {
        Self::new_with_count(kind, msg, 1)
    }

    // Constructor with specified error_count
    pub fn new_with_count(
        kind: ErrorKind,
        msg: String,
        error_count: usize,
    ) -> Self {
        Self {
            kind,
            msg,
            error_count,
            errors: Vec::new(),
            ..Default::default()
        }
    }

    pub fn new_with_multiple_errors(
        kind: ErrorKind,
        msg: String,
        errors: Vec<String>,
    ) -> Self {
        Self {
            kind,
            msg,
            line: String::new(),
            position: 0,
            error_count: errors.len(),
            errors,
        }
    }

    pub fn new_policy_error(msg: String, line: &str, position: usize) -> Self {
        Self {
            kind: ErrorKind::PolicyError,
            line: line.to_string(),
            msg,
            position,
            error_count: 1, // or provide a way to set this if needed
            errors: Vec::new(),
        }
    }

    pub fn kind(&self) -> ErrorKind {
        self.kind
    }

    pub fn msg(&self) -> &str {
        self.msg.as_str()
    }

    pub fn line(&self) -> &str {
        self.line.as_str()
    }

    /// The position of character in line which cause the PolicyError, the
    /// first character is position 0.
    pub fn position(&self) -> usize {
        self.position
    }
}

impl From<serde_json::Error> for NmstateError {
    fn from(e: serde_json::Error) -> Self {
        NmstateError::new(
            ErrorKind::InvalidArgument,
            format!("Invalid propriety: {e}"),
        )
    }
}

impl From<std::net::AddrParseError> for NmstateError {
    fn from(e: std::net::AddrParseError) -> Self {
        NmstateError::new(
            ErrorKind::InvalidArgument,
            format!("Invalid IP address : {e}"),
        )
    }
}
