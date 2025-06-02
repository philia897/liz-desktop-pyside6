use pyo3::prelude::*;

mod flute;
mod tools;
use flute::{BlueBirdResponse, Flute, LizCommand, StateCode};

/// A Python module implemented in Rust.
#[pymodule]
fn bluebird(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_class::<Flute>()?;
    m.add_class::<LizCommand>()?;
    m.add_class::<BlueBirdResponse>()?;
    m.add_class::<StateCode>()?;
    Ok(())
}
