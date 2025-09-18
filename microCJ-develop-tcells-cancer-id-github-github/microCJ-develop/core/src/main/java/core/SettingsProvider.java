package core;

import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.XMLConfiguration;
import org.apache.commons.configuration2.builder.fluent.Configurations;
import org.apache.commons.configuration2.ex.ConfigurationException;
import org.apache.commons.configuration2.io.FileHandler;
import org.apache.commons.configuration2.tree.ImmutableNode;
import org.tinylog.Logger;

import java.io.File;
import java.util.ArrayList;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Singleton class to hold a reference to the settings
 *
 */
public enum SettingsProvider {
	SETTINGS_PROVIDER;

	private static final String DEFAULT_SETTINGS = "default.xml";
	private static String USER_SETTINGS;
	private XMLConfiguration settings;
	private final Configurations settingsHelper = new Configurations();
	private Integer index = 0;

	public XMLConfiguration getSettings() {
		return settings;
	}

	/**
	 * Loads a settings xml file with the given file name. If the file does not exist, an exception is found or settings are null.
	 * @param file the name of the file
	 * @param throwException whether the method will throw an exception if the file is not found.
	 */
	void load(String file, boolean throwException){
		try {
			settings = settingsHelper.xml(new File(file));
		} catch (ConfigurationException e) {
			if(throwException) e.printStackTrace();
			else settings = null;
		}
	}

	void load(String file, boolean throwException, Integer index){
		this.index = index;
		try {
			settings = settingsHelper.xml(new File(file));
		} catch (ConfigurationException e) {
			if(throwException) e.printStackTrace();
			else settings = null;
		}
	}

	/**
	 * Loads the user settings
	 */
	void load() {
		load(USER_SETTINGS, false);
		Logger.info("{} settings loaded", settings == null ? "default" : "user");
		if(settings == null) loadDefaultSettings();
	}

	public static void setUserSettings(String userSettings) {
		USER_SETTINGS = userSettings;
	}

	/**
	 * Loads the default settings
	 */
	public void loadDefaultSettings(){
		System.out.println("loading default settings");
		load(DEFAULT_SETTINGS, true);
		writeUserSettingsToFile();
	}

	/**
	 * Writes current settings to user settings file
	 */
	public void writeUserSettingsToFile() {
		FileHandler handler = new FileHandler(settings);
		File out = new File(USER_SETTINGS);
		try {
			handler.save(out);
		} catch (ConfigurationException e) {
			e.printStackTrace();
		}
	}

	public int getGroupSize(String key){
		return settings.configurationAt(key).size();
	}

	public String getStringFromRawString(String value){
		if(value.startsWith("[") && value.endsWith("]")) {
			value = value.substring(1, value.length() - 1);
			String[] split = value.split("-");
			if (split.length > 1) {
				value = split[index];
			}
		}
		return value;
	}

	public String getString(String key){
		String value = settings.getString(key).strip();
		return getStringFromRawString(value);
	}



	public String getString(String key, String defaultString){
		String result = settings.getString(key);
		return Objects.requireNonNullElse(result, defaultString);
	}

	public int getInt(String key){
		String value = settings.getString(key);
		return getIntFromRawString(value);
	}

	public int getIntFromRawString(String value){
		String pattern = "^\\[(\\d+)-(\\d+),(\\d+)]$";
		Pattern r = Pattern.compile(pattern);
		Matcher m = r.matcher(value);
		if (m.find()) {
			int start = Integer.parseInt(m.group(1));
			int end = Integer.parseInt(m.group(2));
			int period = Integer.parseInt(m.group(3));
			int result = start + index * period;
			if(result > end) {
				throw new IllegalArgumentException("bad string: " + value);
			} else return result;
		} else return Integer.parseInt(value);
	}

	public double getDouble(String key){
		String value = settings.getString(key);
		return getDoubleFromRawString(value);
	}

	public double getDoubleFromRawString(String value){
		String pattern = "^\\[(\\d*\\.*\\d*)-(\\d*\\.*\\d*),(\\d*\\.*\\d*)]$";
		Pattern r = Pattern.compile(pattern);
		Matcher m = r.matcher(value);
		if (m.find()) {
			double start = Double.parseDouble(m.group(1));
			double end = Double.parseDouble(m.group(2));
			double period = Double.parseDouble(m.group(3));
			double result = start + index * period;
			if(result > end) {
				throw new IllegalArgumentException("bad string: " + value);
			} else return result;
		} else return Double.parseDouble(value);
	}

	public boolean getBoolean(String key) {
		String value = settings.getString(key);
		return getBooleanFromRawString(value);
	}

	public boolean getBooleanFromRawString(String value){
		String[] split = value.split("-");
		if(split.length > 1){
			if(split.length > 2){
				throw new IllegalArgumentException("bad string: " + value);
			}
			value = split[index];
		}
		return Boolean.parseBoolean(value);
	}

	public String getGeneralString(String key){
		return getString("general." + key);
	}

	public int getGeneralInt(String key){
		return getInt("general." + key);
	}

	public double getGeneralDouble(String key){
		return getDouble("general." + key);
	}

	public boolean getGeneralBoolean(String key){
		return getBoolean("general." + key);
	}


}
