use pyo3::prelude::*;

use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::tools::{
    db::{MusicSheetDB, Shortcut, UserSheet},
    exec::{convert_shortcut_to_keycode, execute_shortcut_enigo},
    rhythm::{parse_rhythm, Rhythm},
    utils::{generate_id, id_to_string, string_to_id, create_liz_folder},
};

#[pyclass(eq, eq_int)]
#[derive(Serialize, Deserialize, Debug, PartialEq, Clone)]
pub enum StateCode {
    OK,
    FAIL,
    BUG,
}

// Implement Display for StateCode to allow it to be printed
impl fmt::Display for StateCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let state_str = match *self {
            StateCode::OK => "OK",
            StateCode::FAIL => "FAIL",
            StateCode::BUG => "BUG",
        };
        write!(f, "{}", state_str)
    }
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug)]
pub struct LizCommand {
    #[pyo3(get, set)]
    pub action: String,
    #[pyo3(get, set)]
    pub args: Vec<String>,
}

#[pymethods]
impl LizCommand {
    #[new]
    pub fn new(action: String, args: Vec<String>) -> Self {
        LizCommand { action, args }
    }

    #[pyo3(name = "__repr__")]
    pub fn repr(&self) -> String {
        format!("LizCommand(action={}, args={:?})", self.action, self.args)
    }
}

#[pyclass]
#[derive(Serialize, Deserialize, Debug)]
pub struct BlueBirdResponse {
    #[pyo3(get, set)]
    pub code: StateCode,
    #[pyo3(get, set)]
    pub results: Vec<String>,
}

#[pymethods]
impl BlueBirdResponse {
    #[new]
    pub fn new(code: StateCode, results: Vec<String>) -> Self {
        BlueBirdResponse { code, results }
    }

    #[staticmethod]
    pub fn success() -> Self {
        BlueBirdResponse {
            code: StateCode::OK,
            results: vec![],
        }
    }

    #[pyo3(name = "__repr__")]
    pub fn repr(&self) -> String {
        format!("BlueBirdResponse(code={:?}, results={:?})", self.code, self.results)
    }
}

#[derive(Debug)]
pub struct FluteExecuteError {
    msg: String,
    code: StateCode,
}

impl FluteExecuteError {
    // Constructor to create a new FluteExecuteError
    pub fn new(msg: &str, code: StateCode) -> Self {
        FluteExecuteError {
            msg: msg.to_string(),
            code,
        }
    }

    // Method to get the error message
    pub fn message(&self) -> &str {
        &self.msg
    }

    // Method to get the state code
    pub fn code(&self) -> &StateCode {
        &self.code
    }
}

// Implement the Display trait to format the error message
impl fmt::Display for FluteExecuteError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.code(), self.message())
    }
}

// Implement the Error trait for FluteExecuteError
impl Error for FluteExecuteError {}

// Convert Rust error to Python exception
impl std::convert::From<FluteExecuteError> for PyErr {
    fn from(err: FluteExecuteError) -> PyErr {
        pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
    }
}

#[pyclass]
#[derive(Debug)]
pub struct Flute {
    pub music_sheet: MusicSheetDB,
    pub rhythm: Rhythm,
}

#[pymethods]
impl Flute {
    #[staticmethod]
    pub fn create_flute(rhythm_path: Option<String>) -> PyResult<Flute> {
        let rhythm: Rhythm = Rhythm::read_rhythm(rhythm_path)
                .map_err(|e| 
                    FluteExecuteError::new(&e.to_string(), StateCode::FAIL)
                )?;
    
        if let Err(e) = create_liz_folder(&rhythm.liz_path) {
            eprintln!("Failed to get liz working dir because: {}", e);
            std::process::exit(1);
        }
    
        let music_sheet_path = &rhythm.music_sheet_path;
        let mut flute: Flute = Flute {
            music_sheet: MusicSheetDB::import_from_json(music_sheet_path).unwrap_or_else(|_| {
                eprintln!("Failed to load music sheet from {}", music_sheet_path);
                MusicSheetDB::new() // Return a default instance if loading fails
            }),
            rhythm: rhythm,
        };
        flute.calibrate();
        flute.music_sheet.read_keymap(&flute.rhythm.keymap_path);
        Ok(flute)
    }

    pub fn get_trigger_hotkey(&self) -> String {
        return self.rhythm.trigger_shortcut.clone();
    }

    pub fn get_theme(&self) -> String {
        return self.rhythm.theme.clone();
    }

    pub fn play(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        match cmd.action.as_str() {
            // "get_shortcuts" => self.command_get_shortcuts(cmd),
            // "reload" => self.command_reload(cmd),
            "execute" => self.command_execute(cmd),
            "persist" => self.command_persist(cmd),
            "info" => self.command_info(cmd),
            "get_shortcut_details" => self.command_get_shortcut_details(cmd),
            "new_id" => self.command_new_id(cmd),
            "create_shortcuts" => self.command_create_shortcuts(cmd),
            "update_shortcuts" => self.command_update_shortcuts(cmd),
            "delete_shortcuts" => self.command_delete_shortcuts(cmd),
            "get_deleted_shortcut_details" => self.command_get_deleted_shortcut_details(cmd),
            "export_shortcuts" => self.command_export_shortcuts(cmd),
            "import_shortcuts" => self.command_import_shortcuts(cmd),
            "update_rhythm" => self.command_update_rhythm(cmd),
            _ => self.command_default(cmd),
        }
    }
}

impl Flute {

    fn calibrate(&mut self) {
        self.update_rank();
    }

    fn update_rank(&mut self) {
        self.music_sheet.sort_by_column("application", true);
        self.music_sheet.sort_by_column("hit_number", false);
    }

    fn _get_sc_by_id(&self, id_str: &str) -> Result<Shortcut, Box<dyn Error>> {
        let id: u128 = string_to_id(id_str)?;
        let r: &Shortcut = self
            .music_sheet
            .retrieve(id, None)
            .ok_or("Id does not exist".to_string())?;
        Ok(r.clone())
    }

    fn command_export_shortcuts(&self, cmd: &LizCommand) -> BlueBirdResponse {
        fn split_vec(vec: &Vec<String>) -> Option<(String, Vec<String>)> {
            let (first, rest) = vec.split_first()?; // Get first element and the rest
            Some((first.clone(), rest.to_vec())) // Clone to return owned values
        }
        if let Some((file_path, id_list)) = split_vec(&cmd.args) {
            let sc_to_export: Result<Vec<Shortcut>, _> = id_list
                .iter()
                .map(|id_str| self._get_sc_by_id(&id_str))
                .collect();
            match sc_to_export {
                Ok(sc_to_export) => {
                    println!("Export to {}", file_path);
                    let sheet = UserSheet::new(sc_to_export);
                    match sheet.export_to_json(&file_path) {
                        Ok(_) => BlueBirdResponse::success(),
                        Err(e) => {
                            let err_str = format!("Failed to export to {}: {}", file_path, e);
                            eprintln!("Export Shortcuts: {}", err_str);
                            BlueBirdResponse {
                                code: StateCode::BUG,
                                results: vec![err_str],
                            }
                        }
                    }
                }
                Err(e) => {
                    let err_str = format!("Failed to parse id: {}", e);
                    eprintln!("Export Shortcuts: {}", err_str);
                    BlueBirdResponse {
                        code: StateCode::BUG,
                        results: vec![err_str],
                    }
                }
            }
        } else {
            BlueBirdResponse {
                code: StateCode::BUG,
                results: vec!["File path is not given".to_string()],
            }
        }
    }

    fn command_import_shortcuts(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        if cmd.args.is_empty() {
            eprintln!("BUG: Empty args, expect one file_path");
            return BlueBirdResponse {
                code: StateCode::BUG,
                results: vec!["Empty args, expect one shortcut id".to_string()],
            };
        }
        println!("Import from {:?}", cmd.args);
        let mut failed_paths: Vec<String> = Vec::new();
        for file in cmd.args.iter() {
            match UserSheet::import_from(file) {
                Ok(sheet) => {
                    sheet.transform_to_db(&mut self.music_sheet);
                }
                Err(e) => {
                    let err_str = format!("Failed to import file {}: {}", file, e);
                    eprintln!("Export Shortcuts: {}", err_str);
                    failed_paths.push(file.clone());
                }
            }
        }
        if failed_paths.is_empty() {
            BlueBirdResponse::success()
        } else {
            BlueBirdResponse {
                code: StateCode::FAIL,
                results: failed_paths,
            }
        }
    }

    // fn command_get_shortcuts(&self, cmd: &LizCommand) -> BlueBirdResponse {
    //     let fmt = &self.rhythm.shortcut_print_fmt;
    //     let shortcuts = if cmd.args.is_empty() {
    //         self.music_sheet.retrieve_all()
    //     } else {
    //         self.music_sheet.fuzzy_search(&cmd.args[0])
    //     };
    //     let sc_vec: Vec<String> = shortcuts
    //         .into_iter()
    //         .map(|sc| {
    //             // Create a JSON string
    //             sc.to_json_string_simple(fmt)
    //         })
    //         .collect();
    //     BlueBirdResponse {
    //         code: StateCode::OK,
    //         results: sc_vec,
    //     }
    // }

    fn command_get_shortcut_details(&self, cmd: &LizCommand) -> BlueBirdResponse {
        let shortcuts = if cmd.args.is_empty() {
            self.music_sheet.retrieve_all()
        } else {
            self.music_sheet.fuzzy_search(&cmd.args[0])
        };
        let sc_vec: Vec<String> = shortcuts
            .into_iter()
            .map(|sc| sc.to_json_string())
            .collect();
        BlueBirdResponse {
            code: StateCode::OK,
            results: sc_vec,
        }
    }

    fn command_get_deleted_shortcut_details(&self, _cmd: &LizCommand) -> BlueBirdResponse {
        let shortcuts = self.music_sheet.retrieve_deleted();
        let sc_vec: Vec<String> = shortcuts
            .into_iter()
            .map(|sc| sc.to_json_string())
            .collect();
        BlueBirdResponse {
            code: StateCode::OK,
            results: sc_vec,
        }
    }

    fn command_new_id(&self, _cmd: &LizCommand) -> BlueBirdResponse {
        BlueBirdResponse {
            code: StateCode::OK,
            results: vec![id_to_string(generate_id())],
        }
    }

    fn _args_to_shortcut_vec(&self, cmd: &LizCommand) -> Result<Vec<Shortcut>, String> {
        let shortcuts: Result<Vec<Shortcut>, _> = cmd
            .args
            .iter()
            .map(|sc_str| Shortcut::from_json_string(&sc_str))
            .collect();
        match shortcuts {
            Ok(shortcuts) => Ok(shortcuts),
            Err(e) => {
                let err_str = format!("Failed to parse shortcut: {}", e);
                Err(err_str)
            }
        }
    }

    fn command_create_shortcuts(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        match self._args_to_shortcut_vec(cmd) {
            Ok(shortcuts) => {
                self.music_sheet.add_shortcuts(shortcuts, None);
                BlueBirdResponse::success()
            }
            Err(e) => {
                eprintln!("Create Shortcuts: {}", e);
                BlueBirdResponse {
                    code: StateCode::BUG,
                    results: vec![e],
                }
            }
        }
    }

    fn command_update_shortcuts(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        match self._args_to_shortcut_vec(cmd) {
            Ok(shortcuts) => {
                let unmatched: Vec<Shortcut> = self.music_sheet.update_shortcuts(shortcuts);
                let unmatched: Vec<String> =
                    unmatched.iter().map(|sc| sc.to_json_string()).collect();
                if unmatched.is_empty() {
                    BlueBirdResponse {
                        code: StateCode::OK,
                        results: unmatched,
                    }
                } else {
                    eprintln!("Unmatched: {:?}", unmatched);
                    BlueBirdResponse {
                        code: StateCode::FAIL,
                        results: unmatched,
                    }
                }
            }
            Err(e) => {
                eprintln!("Update Shortcuts: {}", e);
                BlueBirdResponse {
                    code: StateCode::BUG,
                    results: vec![e],
                }
            }
        }
    }

    fn command_delete_shortcuts(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        let id_to_delete: Result<Vec<u128>, _> = cmd
            .args
            .iter()
            .map(|id_str| string_to_id(&id_str))
            .collect();
        match id_to_delete {
            Ok(id_to_delete) => {
                self.music_sheet.delete_shortcuts(id_to_delete);
                BlueBirdResponse::success()
            }
            Err(e) => {
                let err_str = format!("Failed to parse id: {}", e);
                eprintln!("Delete Shortcuts: {}", err_str);
                BlueBirdResponse {
                    code: StateCode::BUG,
                    results: vec![err_str],
                }
            }
        }
    }

    fn command_update_rhythm(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        if cmd.args.is_empty() {
            return BlueBirdResponse {
                code: StateCode::BUG,
                results: vec![format!("Settings is missing")]
            }
        }

        let new_rhythm = parse_rhythm(&cmd.args[0]);
        match new_rhythm {
            Ok(new_rhythm) => {
                let saved_path = new_rhythm.save_rhythm(None); // Save to the default path
                self.rhythm = new_rhythm;
                match saved_path {
                    Ok(saved_path) => BlueBirdResponse {
                        code: StateCode::OK,
                        results: vec![saved_path]
                    },
                    Err(e) => {
                        let err_msg = format!("Failed to save rhythm to {}\nError: {}", &cmd.args[0], e);
                        BlueBirdResponse {
                        code: StateCode::FAIL,
                        results: vec![err_msg]
                        }
                    }
                }
                
            },
            Err(e) => {
                let err_msg = format!("Failed to parse rhythm: {}\nError: {}", cmd.args[0], e);
                eprint!("{}", err_msg);
                BlueBirdResponse {
                    code: StateCode::BUG,
                    results: vec![err_msg]
                }
            },
        }
    }

    /// Execute the shortcut of given id
    fn _execute(&mut self, id_str: &str) -> Result<&Shortcut, FluteExecuteError> {
        match string_to_id(id_str) {
            Ok(id) => {
                let sc = self.music_sheet.retrieve(id, None);
                if sc.is_none() {
                    return Err(FluteExecuteError::new(
                        &format!("No keycode found for id {}", id_str),
                        StateCode::BUG,
                    ));
                }
                let sc: &Shortcut = sc.unwrap();
                let keycode = convert_shortcut_to_keycode(&sc.shortcut, &self.music_sheet.keymap);
                println!("Execute: {}: {}", id_str, keycode);
                if let Err(e) = execute_shortcut_enigo(&keycode, self.rhythm.interval_ms) {
                    let err_str =
                        format!("Enigo fails to execute shortcut {}: {}", sc.shortcut, e);
                    return Err(FluteExecuteError::new(&err_str, StateCode::FAIL));
                }
                let _ = self.music_sheet.hit_num_up(id);
                self.update_rank();
                let sc = self.music_sheet.retrieve(id, None).unwrap();
                Ok(sc)
            }
            Err(e) => {
                let err_str = format!("BUG: Failed to parse ID {}: {}", id_str, e);
                Err(FluteExecuteError::new(&err_str, StateCode::BUG))
            }
        }
    }

    fn command_execute(&mut self, cmd: &LizCommand) -> BlueBirdResponse {
        if cmd.args.is_empty() {
            eprintln!("BUG: Empty args, expect one index on args[0]");
            return BlueBirdResponse {
                code: StateCode::BUG,
                results: vec!["Empty args, expect one shortcut id".to_string()],
            };
        }
        match self._execute(cmd.args[0].as_str()) {
            Ok(sc) => {
                BlueBirdResponse {
                    code: StateCode::OK,
                    results: vec![
                        sc.to_json_string()
                    ]
                }
            },
            Err(e) => {
                eprint!("Execute: {}", e);
                BlueBirdResponse {
                    results: vec![e.message().to_string()],
                    code: e.code,
                }
            }
        }
    }

    fn persist(&self) -> Result<(), Box<dyn std::error::Error>> {
        self.music_sheet
            .export_to_json(&self.rhythm.music_sheet_path)
    }

    fn command_persist(&self, _cmd: &LizCommand) -> BlueBirdResponse {
        match self.persist() {
            Ok(()) => BlueBirdResponse::success(),
            Err(e) => {
                eprintln!("BUG: Failed to persist music_sheet, error: {}", e);
                BlueBirdResponse {
                    code: StateCode::BUG,
                    results: vec!["Failed to persist music_sheet".to_string()],
                }
            }
        }
    }

    fn command_info(&self, _cmd: &LizCommand) -> BlueBirdResponse {
        let r: &Rhythm = &self.rhythm;
        BlueBirdResponse {
            code: StateCode::OK,
            results: r.to_string_list(),
        }
    }

    fn command_default(&self, cmd: &LizCommand) -> BlueBirdResponse {
        eprint!("Invalid Cmd: {:#?}", cmd);
        BlueBirdResponse {
            code: StateCode::BUG,
            results: vec![format!("Invalid Liz Cmd: {}", cmd.action)],
        }
    }
}

// Implement the Drop trait for Flute
// impl Drop for Flute {
//     fn drop(&mut self) {
//         // Attempt to save the music_sheet when the Flute instance is dropped
//         let file_path: &String = &self.rhythm.music_sheet_path;
//         if let Err(e) = self.music_sheet.export_to_json(file_path) {
//             eprintln!("Failed to save music sheet in Drop: {}", e);
//         } else {
//             println!("Music sheet saved successfully in Drop.");
//         }
//     }
// }
