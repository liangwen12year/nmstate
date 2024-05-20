// SPDX-License-Identifier: Apache-2.0
use serde::ser;
use serde_yaml;
use std::io;
use std::string::FromUtf8Error;
use serde::ser::Error as SerError; // Import the SerError trait

pub fn to_string_with_error_count<T>(value: &T) -> Result<(String, usize), serde_yaml::Error>
where
    T: ?Sized + ser::Serialize,
{
    let mut vec = Vec::with_capacity(128);
    let mut error_count = 0;

    struct ErrorCountingWriter<'a> {
        writer: &'a mut Vec<u8>,
        error_count: &'a mut usize,
    }

    impl<'a> io::Write for ErrorCountingWriter<'a> {
        fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
            self.writer.write(buf).map_err(|e| {
                *self.error_count += 1;
                e
            })
        }

        fn flush(&mut self) -> io::Result<()> {
            self.writer.flush()
        }
    }

    let mut writer = ErrorCountingWriter { writer: &mut vec, error_count: &mut error_count };
    serde_yaml::to_writer(&mut writer, value)?;
    let yaml_string = String::from_utf8(vec).map_err(convert_utf8_error)?;

    Ok((yaml_string, error_count))
}

fn convert_utf8_error(error: FromUtf8Error) -> serde_yaml::Error {
    serde_yaml::Error::custom(format!("UTF-8 conversion error: {}", error))
}

use crate::{error::CliError, state::state_from_file};

pub(crate) fn format(state_file: &str) -> Result<String, CliError> {
    let state = state_from_file(state_file)?;
    let (yaml_string, error_count) = to_string_with_error_count(&state)?;
    Ok(yaml_string)
}
